import os
import json
from flask import Flask, render_template, request, redirect, url_for, jsonify, send_file, session
from sqlalchemy import create_engine, MetaData, Table
from sqlalchemy_views import CreateView, DropView
from sqlalchemy.sql import text
from config import Config
from models import db, User, Recipe, Ingredient, RecipeIngredient, Favourite, Rating
from datetime import datetime
import re

app = Flask(__name__)
app.config.from_object(Config)
db.init_app(app)
engine = create_engine('sqlite:///instance/yourdatabase.db')

def export_db():
    data = {
        'users': [user.__dict__ for user in User.query.all()],
        'recipes': [recipe.__dict__ for recipe in Recipe.query.all()],
        'ingredients': [ingredient.__dict__ for ingredient in Ingredient.query.all()],
        'recipe_ingredients': [ri.__dict__ for ri in RecipeIngredient.query.all()],
        'favourites': [f.__dict__ for f in Favourite.query.all()],
        'ratings': [r.__dict__ for r in Rating.query.all()]
    }

    for table in data.values():
        for entry in table:
            entry.pop('_sa_instance_state', None)
    with open('db_export.json', 'w') as f:
        json.dump(data, f)

def import_db():
    if not os.path.exists('db_export.json'):
        return
    with open('db_export.json', 'r') as f:
        data = json.load(f)
    
    db.drop_all()
    db.create_all()

    for user_data in data['users']:
        user = User(**user_data)
        db.session.add(user)

    for recipe_data in data['recipes']:
        recipe = Recipe(**recipe_data)
        db.session.add(recipe)

    for ingredient_data in data['ingredients']:
        ingredient = Ingredient(**ingredient_data)
        db.session.add(ingredient)

    for ri_data in data['recipe_ingredients']:
        ri = RecipeIngredient(**ri_data)
        db.session.add(ri)

    for favourite_data in data['favourites']:
        favourite = Favourite(**favourite_data)
        db.session.add(favourite)

    for rating_data in data['ratings']:
        rating = Rating(**rating_data)
        db.session.add(rating)

    db.session.commit()


def create_database_views():
    definition = text("SELECT id, name, dish_category, cuisine, avg_rating FROM recipe LEFT JOIN (SELECT recipe_id, AVG(rating) AS avg_rating FROM rating GROUP BY recipe_id) AS r ON r.recipe_id = recipe.id")
    with engine.connect() as connection:
        # Execute your query using the connection
        view_drop = text(f"DROP VIEW my_view")
        connection.execute(view_drop)
        view_query = text(f"CREATE VIEW IF NOT EXISTS my_view AS {definition} ")
        connection.execute(view_query)

@app.teardown_appcontext
def shutdown_session(exception=None):
    export_db()

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        user = User.query.filter_by(username=username).first()
        # Example authentication (replace with your actual authentication logic)
        if user and user.check_password(password):
            session['username'] = username  # Store the username in the session
            return redirect(url_for('user', user_id=user.username))
        else:
            return render_template('login.html', error='Invalid username or password')

    return render_template('login.html')

@app.route('/export_db')
def export_db_route():
    export_db()
    return send_file('db_export.json', as_attachment=True)

@app.route('/import_db')
def import_db_route():
    import_db()
    return redirect(url_for('index'))
'''
@app.route('/')
def index():
    users = User.query.all()
    recipes = Recipe.query.all()
    return render_template('index.html', users=users, recipes=recipes)
'''
@app.route('/')
def home():
    return render_template('home.html')


@app.route('/user/<string:user_id>/recipe')
def recipes(user_id):
    recipes = Recipe.query.all()
    user = User.query.get_or_404(user_id)
    return render_template('all_recipes.html', recipes=recipes, user=user)

@app.route('/search_recipes', methods=['GET'])
def search_recipes():
    query = request.args.get('query', '')
    if not query:
        return redirect(url_for('recipes'))  # Redirect to the recipes page if no query is provided

    # Perform the search using regular expressions
    regex = re.compile(query, re.IGNORECASE)  # Compile the regular expression pattern
    matched_recipes = [recipe for recipe in Recipe.query.all() if regex.search(recipe.name) or regex.search(recipe.dish_category) or regex.search(recipe.cuisine)]

    return render_template('all_recipes.html', recipes=matched_recipes)

@app.route('/user/<string:user_id>')
def user(user_id):
    user = User.query.get_or_404(user_id)
    favorites = Favourite.query.filter_by(user_id = user_id).all()
    with engine.connect() as connection:
        # Execute your query using the connection
        view_query = text("SELECT * FROM my_view ORDER BY avg_rating DESC LIMIT 5")
        popular_recipes = connection.execute(view_query).fetchall()

    return render_template('user.html', user=user, favorites = favorites, popular_recipes = popular_recipes)

@app.route('/user/<string:user_id>/recipe/<int:recipe_id>')
def recipe(user_id, recipe_id):
    user = User.query.get_or_404(user_id)
    recipe = Recipe.query.get_or_404(recipe_id)
    ratings = Rating.query.filter_by(recipe_id=recipe_id).all()
    if ratings:
        average_rating = sum(r.rating for r in ratings) / len(ratings)
        average_rating_stars = ''.join(['&#9733;' if i < round(average_rating) else '&#9734;' for i in range(5)])
    else:
        average_rating = 0
        average_rating_stars = '&#9734;&#9734;&#9734;&#9734;&#9734;'
    return render_template('recipe.html', recipe=recipe, average_rating=average_rating, average_rating_stars=average_rating_stars)

@app.route('/user/<string:user_id>/rate_recipe/<int:recipe_id>', methods=['POST'])
def rate_recipe(user_id, recipe_id):
    rating_value = int(request.form['rating'])
    existing_rating = Rating.query.filter_by(user_id=user_id, recipe_id=recipe_id).first()

    if existing_rating:
        existing_rating.rating = rating_value
    else:
        new_rating = Rating(user_id=user_id, recipe_id=recipe_id, rating=rating_value)
        db.session.add(new_rating)

    db.session.commit()
    return redirect(url_for('recipe', recipe_id=recipe_id, user_id = user_id))

@app.route('/user/<string:user_id>/rate_recipe/<int:recipe_id>/add_to_favorites', methods=['POST'])
def add_to_favorites(user_id, recipe_id):
    if request.method == 'POST':
        is_favourite = Favourite.query.filter_by(user_id=user_id, recipe_id=recipe_id).first()
        if not is_favourite:
            favorite = Favourite(user_id=user_id, recipe_id=recipe_id)
            db.session.add(favorite)
            db.session.commit()
        
        return redirect(url_for('recipe', recipe_id=recipe_id, user_id = user_id))

@app.route('/add_user', methods=['GET', 'POST'])
def add_user():
    if request.method == 'POST':
        username = request.form['username']
        name = request.form['name']
        password = request.form['password']
        new_user = User(username=username, name=name, password=password)
        db.session.add(new_user)
        db.session.commit()
        return redirect(url_for('login'))
    return render_template('add_user.html')

@app.route('/user/<string:user_id>/add_recipe', methods=['GET', 'POST'])
def add_recipe(user_id):
    if request.method == 'POST':
        name = request.form['name']
        dish_category = request.form['dish_category']
        cuisine = request.form['cuisine']
        cooking_time_hours = int(request.form['cooking_time_hours'])
        cooking_time_minutes = int(request.form['cooking_time_minutes'])
        cooking_time = cooking_time_hours * 60 + cooking_time_minutes
        #user_id = request.form['user_id']

        # Combine steps into a single text entry with step numbers
        steps = request.form.getlist('step_description')
        recipe_steps = "\n".join([f"Step {i+1}: {step}" for i, step in enumerate(steps)])

        new_recipe = Recipe(name=name, dish_category=dish_category, cuisine=cuisine, cooking_time=cooking_time, recipe_steps=recipe_steps, user_id=user_id)
        db.session.add(new_recipe)
        db.session.commit()

        # Adding ingredients to the recipe
        ingredients = request.form.getlist('ingredient_name')
        amounts = request.form.getlist('ingredient_amount')
        for ingredient_name, amount in zip(ingredients, amounts):
            ingredient = Ingredient.query.filter_by(name=ingredient_name).first()
            if not ingredient:
                ingredient = Ingredient(name=ingredient_name)
                db.session.add(ingredient)
                db.session.commit()
            recipe_ingredient = RecipeIngredient(recipe_id=new_recipe.id, ingredient_name=ingredient.name, amount=amount)
            db.session.add(recipe_ingredient)
            db.session.commit()

        return redirect(url_for('user', user_id = user_id))
    #users = User.query.all()
    return render_template('add_recipe.html')

@app.route('/ingredient_suggestions')
def ingredient_suggestions():
    query = request.args.get('query', '')
    if query:
        suggestions = Ingredient.query.filter(Ingredient.name.ilike(f'%{query}%')).all()
        suggestions_list = [ingredient.name for ingredient in suggestions]
        return jsonify(suggestions=suggestions_list)
    return jsonify(suggestions=[])

@app.route('/category_suggestions')
def category_suggestions():
    query = request.args.get('query', '')
    if query:
        suggestions = db.session.query(Recipe.dish_category).filter(Recipe.dish_category.ilike(f'%{query}%')).distinct().all()
        category_list = [category[0] for category in suggestions]
        return jsonify(suggestions=category_list)
    return jsonify(suggestions=[])

@app.route('/cuisine_suggestions')
def cuisine_suggestions():
    query = request.args.get('query', '')
    if query:
        suggestions = db.session.query(Recipe.cuisine).filter(Recipe.cuisine.ilike(f'%{query}%')).distinct().all()
        cuisine_list = [cuisine[0] for cuisine in suggestions]
        return jsonify(suggestions=cuisine_list)
    return jsonify(suggestions=[])

@app.route('/ingredients')
def ingredients():
    ingredients = Ingredient.query.all()
    return render_template('ingredients.html', ingredients=ingredients)

@app.route('/user/<string:user_id>/view_ratings/<int:recipe_id>')
def view_ratings(user_id, recipe_id):
    recipe = Recipe.query.get_or_404(recipe_id)
    ratings = Rating.query.filter_by(recipe_id=recipe_id).all()
    return render_template('view_ratings.html', recipe=recipe, ratings=ratings)

@app.route('/wipe_db')
def wipe_db():
    db.drop_all()
    db.create_all()
    return "Database wiped and recreated!"


if __name__ == '__main__':
    with app.app_context():
        import_db()  # Load data from file if it exists
        create_database_views()
    app.run(debug=True)