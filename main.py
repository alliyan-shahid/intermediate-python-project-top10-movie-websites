from flask import Flask, render_template, redirect, url_for, request
from flask_bootstrap import Bootstrap5
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy import Integer, String, Float
from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField
from wtforms.validators import DataRequired
import requests
import os

# API Configuration - Replace with your own credentials
API_KEY = os.environ.get("TMDB_API_KEY", "your_api_key_here")
BEARER_TOKEN = os.environ.get("TMDB_BEARER_TOKEN", "your_bearer_token_here")

search_url = "https://api.themoviedb.org/3/search/movie"
info_url = "https://api.themoviedb.org/3/movie"
img_url = "https://image.tmdb.org/t/p/w500"

headers = {
    "Authorization": f"Bearer {BEARER_TOKEN}",
    "accept": "application/json"
}

app = Flask(__name__)
# Use environment variable for secret key in production
app.config['SECRET_KEY'] = os.environ.get("FLASK_SECRET_KEY", "dev-key-change-in-production")
Bootstrap5(app)


# Database setup
class Base(DeclarativeBase):
    pass


app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///movies.db'
db = SQLAlchemy(model_class=Base)
db.init_app(app)


# Movie table schema
class Movie(db.Model):
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    title: Mapped[str] = mapped_column(String(250), unique=True, nullable=False)
    year: Mapped[int] = mapped_column(Integer, nullable=False)
    description: Mapped[str] = mapped_column(String(500), nullable=False)
    rating: Mapped[float] = mapped_column(Float, nullable=True)
    ranking: Mapped[int] = mapped_column(Integer, nullable=True)
    review: Mapped[str] = mapped_column(String(250), nullable=True)
    img_url: Mapped[str] = mapped_column(String(250), nullable=False)


with app.app_context():
    db.create_all()


class RateMovieForm(FlaskForm):
    rating = StringField("Your Rating Out of 10 e.g. 7.5", validators=[DataRequired()])
    review = StringField("Your Review", validators=[DataRequired()])
    submit = SubmitField("Done")


class AddMovieForm(FlaskForm):
    title = StringField("Movie Title", validators=[DataRequired()])
    submit = SubmitField("Add Movie")


@app.route("/")
def home():
    # Grab all movies from the database
    result = db.session.execute(db.select(Movie))
    all_movies = result.scalars().all()
    
    # Filter out movies without ratings and sort by rating
    movies_with_ratings = [movie for movie in all_movies if movie.rating is not None]
    movies_with_ratings.sort(key=lambda x: x.rating, reverse=True)
    
    # Assign rankings
    for index, movie in enumerate(movies_with_ratings):
        movie.ranking = index + 1
    
    db.session.commit()
    
    # Display movies in ranking order
    final_result = db.session.execute(db.select(Movie).order_by(Movie.ranking))
    final_movies = final_result.scalars().all()
    
    return render_template("index.html", movies=final_movies)


@app.route("/add", methods=["GET", "POST"])
def add():
    form = AddMovieForm()
    if form.validate_on_submit():
        params = {"query": form.title.data}
        movie_data = requests.get(search_url, headers=headers, params=params).json()["results"]
        return render_template("select.html", options=movie_data)
    return render_template("add.html", form=form)


@app.route("/find")
def find_movie():
    movie_id = request.args.get("id")
    if movie_id:
        response = requests.get(
            f"{info_url}/{movie_id}",
            params={"api_key": API_KEY, "language": "hi-IN"}
        )
        data = response.json()

        new_movie = Movie(
            title=data["title"],
            year=data["release_date"].split("-")[0],
            img_url=f"{img_url}{data['poster_path']}",
            description=data["overview"]
        )
        db.session.add(new_movie)
        db.session.commit()
        return redirect(url_for("edit", id=new_movie.id))


@app.route("/edit/<int:id>", methods=["GET", "POST"])
def edit(id):
    form = RateMovieForm()
    movie = db.get_or_404(Movie, id)

    if request.method == "POST":
        movie.rating = form.rating.data
        movie.review = form.review.data
        db.session.commit()
        return redirect(url_for("home"))

    return render_template("edit.html", form=form, id=id)


@app.route("/delete/<int:id>")
def delete(id):
    movie = db.get_or_404(Movie, id)
    db.session.delete(movie)
    db.session.commit()
    return redirect(url_for("home"))


if __name__ == '__main__':
    app.run(debug=True)
