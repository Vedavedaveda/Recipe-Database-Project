from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

class User(db.Model):
    username = db.Column(db.String(80), primary_key=True, nullable=False)
    name = db.Column(db.String(120), nullable=False)
    password = db.Column(db.String(128), nullable=False)
    recipes = db.relationship('Recipe', backref='poster', lazy=True)
    favourites = db.relationship('Favourite', backref='user', lazy=True)
    ratings = db.relationship('Rating', backref='user', lazy=True)

    def check_password(self, password):
        return self.password == password

    def __repr__(self):
        return f'<User {self.username}>'

class Recipe(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    dish_category = db.Column(db.String(50), nullable=False)
    cuisine = db.Column(db.String(50), nullable=False)
    cooking_time = db.Column(db.Integer, nullable=False)  # cooking time in minutes
    recipe_steps = db.Column(db.Text, nullable=False)
    user_id = db.Column(db.String(80), db.ForeignKey('user.username'), nullable=False)
    ingredients = db.relationship('RecipeIngredient', backref='recipe', lazy=True)
    favourites = db.relationship('Favourite', backref='recipe', lazy=True)
    ratings = db.relationship('Rating', backref='recipe', lazy=True)

    def __repr__(self):
        return f'<Recipe {self.name}>'

class Ingredient(db.Model):
    name = db.Column(db.String(100), primary_key=True, nullable=False)
    recipes = db.relationship('RecipeIngredient', backref='ingredient', lazy=True)

    def __repr__(self):
        return f'<Ingredient {self.name}>'

class RecipeIngredient(db.Model):
    recipe_id = db.Column(db.Integer, db.ForeignKey('recipe.id'), primary_key=True, nullable=False)
    ingredient_name = db.Column(db.String(100), db.ForeignKey('ingredient.name'), primary_key=True, nullable=False)
    amount = db.Column(db.String(50), nullable=False)  # e.g., "2 cups", "3 tbsp"

    def __repr__(self):
        return f'<RecipeIngredient {self.amount}>'

class Favourite(db.Model):
    user_id = db.Column(db.String(80), db.ForeignKey('user.username'), primary_key=True, nullable=False)
    recipe_id = db.Column(db.Integer, db.ForeignKey('recipe.id'), primary_key=True, nullable=False)

    def __repr__(self):
        return f'<Favourite user={self.user_id} recipe={self.recipe_id}>'

class Rating(db.Model):
    user_id = db.Column(db.String(80), db.ForeignKey('user.username'), primary_key=True, nullable=False)
    recipe_id = db.Column(db.Integer, db.ForeignKey('recipe.id'), primary_key=True, nullable=False)
    rating = db.Column(db.Integer, nullable=False)  # rating between 0 to 5

    def __repr__(self):
        return f'<Rating user={self.user_id} recipe={self.recipe_id} rating={self.rating}>'
