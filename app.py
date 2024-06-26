import os
import json
from flask import Flask, render_template, request, redirect, url_for, jsonify, send_file
from config import Config
from models import db, User, Recipe, Ingredient, RecipeIngredient, Favourite, Rating
from datetime import datetime

app = Flask(__name__)
app.config.from_object(Config)
db.init_app(app)

def export_db():
    data = {
        'users': [user.__dict__ for user in User.query.all()],
        'recipes': [recipe.__dict__ for recipe in Recipe.query.all()],
        'ingredients': [ingredient.__dict__ for ingredient in Ingredient.query.all()],
        'recipe_ingredients': [ri.__dict__ for ri in RecipeIngredient.query.all()],
        'favourites': [f.__dict__ for f in Favourite.query.all()],
        'ratings': [r.__dict__ for r in Rating.query.all()]
    }
    # Remove the '_sa_instance_state' key added by SQLAlchemy
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

@app.route('/export_db')
def export_db_route():
    export_db()
    return send_file('db_export.json', as_attachment=True)

@app.route('/import_db')
def import_db_route():
    import_db()
    return redirect(url_for('index'))

@app.route('/')
def index():
    users = User.query.all()
    recipes = Recipe.query.all()
    return render_template('index.html', users=users, recipes=recipes)

@app.route('/user/<string:user_id>')
def user(user_id):
    user = User.query.get_or_404(user_id)
    return render_template('user.html', user=user)

@app.route('/recipe/<int:recipe_id>')
def recipe(recipe_id):
    recipe = Recipe.query.get_or_404(recipe_id)
    ratings = Rating.query.filter_by(recipe_id=recipe_id).all()
    users = User.query.all()
    if ratings:
        average_rating = sum(r.rating for r in ratings) / len(ratings)
        average_rating_stars = ''.join(['&#9733;' if i < round(average_rating) else '&#9734;' for i in range(5)])
    else:
        average_rating = 0
        average_rating_stars = '&#9734;&#9734;&#9734;&#9734;&#9734;'
    return render_template('recipe.html', recipe=recipe, average_rating=average_rating, average_rating_stars=average_rating_stars, users=users)

@app.route('/rate_recipe/<int:recipe_id>', methods=['POST'])
def rate_recipe(recipe_id):
    user_id = request.form['user_id']
    rating_value = int(request.form['rating'])
    existing_rating = Rating.query.filter_by(user_id=user_id, recipe_id=recipe_id).first()

    if existing_rating:
        existing_rating.rating = rating_value
    else:
        new_rating = Rating(user_id=user_id, recipe_id=recipe_id, rating=rating_value)
        db.session.add(new_rating)

    db.session.commit()
    return redirect(url_for('recipe', recipe_id=recipe_id))

@app.route('/add_user', methods=['GET', 'POST'])
def add_user():
    if request.method == 'POST':
        username = request.form['username']
        name = request.form['name']
        new_user = User(username=username, name=name)
        db.session.add(new_user)
        db.session.commit()
        return redirect(url_for('index'))
    return render_template('add_user.html')

@app.route('/add_recipe', methods=['GET', 'POST'])
def add_recipe():
    if request.method == 'POST':
        name = request.form['name']
        dish_category = request.form['dish_category']
        cuisine = request.form['cuisine']
        cooking_time_hours = int(request.form['cooking_time_hours'])
        cooking_time_minutes = int(request.form['cooking_time_minutes'])
        cooking_time = cooking_time_hours * 60 + cooking_time_minutes
        user_id = request.form['user_id']

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

        return redirect(url_for('index'))
    users = User.query.all()
    return render_template('add_recipe.html', users=users)

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
        suggestions = Recipe.query.filter(Recipe.dish_category.ilike(f'%{query}%')).distinct().all()
        category_list = [category.dish_category for category in suggestions]
        return jsonify(category_list)
    return jsonify([])

@app.route('/cuisine_suggestions')
def cuisine_suggestions():
    query = request.args.get('query', '')
    if query:
        suggestions = Recipe.query.filter(Recipe.cuisine.ilike(f'%{query}%')).distinct().all()
        cuisine_list = [cuisine.cuisine for cuisine in suggestions]
        return jsonify(cuisine_list)
    return jsonify([])

@app.route('/ingredients')
def ingredients():
    ingredients = Ingredient.query.all()
    return render_template('ingredients.html', ingredients=ingredients)

@app.route('/view_ratings/<int:recipe_id>')
def view_ratings(recipe_id):
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
    app.run(debug=True)
