import sqlite3
from flask import Flask, jsonify, render_template, request

app = Flask(__name__)


def get_db_connection():
  conn = sqlite3.connect("recipes.db")
  conn.row_factory = sqlite3.Row
  return conn


@app.route("/api/recipes", methods=["GET"])
def get_recipes():
  cuisine = request.args.get("cuisine")
  diet = request.args.get("diet")
  keyword = request.args.get("keyword")

  query = "SELECT * FROM recipes WHERE 1=1"
  params = []

  if cuisine and cuisine != "全部":
    query += " AND cuisine_type = ?"
    params.append(cuisine)
  if diet and diet != "全部":
    query += " AND diet_type = ?"
    params.append(diet)
  if keyword:
    query += " AND (title LIKE ? OR tags LIKE ?)"
    keyword_param = f"%{keyword}%"
    params.extend([keyword_param, keyword_param])

  conn = get_db_connection()
  recipes = conn.execute(query, params).fetchall()

  result = []
  for r in recipes:
    recipe_id = r["id"]

    ing_rows = conn.execute(
        "SELECT group_name, item_name, amount FROM ingredients WHERE recipe_id"
        " = ? ORDER BY group_name, id",
        (recipe_id,),
    ).fetchall()
    ingredients = [dict(row) for row in ing_rows]

    inst_rows = conn.execute(
        "SELECT step_number, description FROM instructions WHERE recipe_id = ?"
        " ORDER BY step_number ASC",
        (recipe_id,),
    ).fetchall()
    instructions = [dict(row) for row in inst_rows]

    result.append({
        "id": r["id"],
        "title": r["title"],
        "cuisine_type": r["cuisine_type"],
        "diet_type": r["diet_type"],
        "tags": r["tags"].split(",") if r["tags"] else [],
        "ingredients": ingredients,
        "instructions": instructions,
    })

  conn.close()
  return jsonify(result)


@app.route("/")
def index():
  # Flask 會自動去 templates/ 資料夾底下找 index.html
  return render_template("index.html")


if __name__ == "__main__":
  app.run(debug=True)