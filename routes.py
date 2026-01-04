import datetime
import uuid
from flask import Blueprint, render_template, request, redirect, url_for, current_app

pages = Blueprint("tasks", __name__, template_folder="templates", static_folder="static")

@pages.context_processor
def add_calc_date_range():
    def date_range(start: datetime.datetime):
        dates = [start + datetime.timedelta(days=diff) for diff in range(-3, 4)]
        return dates
    return {"date_range": date_range}

def today_at_midnight():
    today = datetime.datetime.today()
    return datetime.datetime(today.year, today.month, today.day)

# Home page
@pages.route("/")
def index():
    date_str = request.args.get("date")
    # get selected_date or today (by default)
    if date_str:
        selected_date = datetime.datetime.fromisoformat(date_str)
    else:
        selected_date = today_at_midnight()
    
    # get all tasks from the selected_date
    tasks_on_date = list(current_app.db.tasks.find({"date": selected_date}))

    # gather all the completed task on the selected_date
    completions = []
    for task in current_app.db.completions.find({"date": selected_date}):
        completions.append(task["task_id"])

    kwargs = {
        "tasks": tasks_on_date,
        "title": "Todo List - Home",
        "selected_date": selected_date,
        "completions": completions,
    }
    return render_template("index.html", **kwargs)

# add a new task to the selected date
@pages.route("/add", methods=["GET", "POST"])
def add_task():
    # get a date from url and convert it to datetime object
    date_str = request.args.get("date")
    selected_date = datetime.datetime.fromisoformat(date_str)

    # if a user submits a new task, save it to tasks database
    if request.method == "POST":
        # PK = "_id"
        current_app.db.tasks.insert_one(
            {"_id": uuid.uuid4().hex, "date": selected_date, "task_description": request.form.get("todo")}
        )
        return redirect(url_for("tasks.index", date=date_str))

    # renders add_task.html
    return render_template(
        "add_task.html", 
        title="Todo List - Add Task", 
        selected_date=selected_date,
    )

# update an existing task
@pages.route("/update", methods=["GET", "POST"])
def update_task():
    date_str = request.form.get("date")
    task_id = request.form.get("task_id")
    new_text = request.form.get("task_description")
    print(new_text)
    current_app.db.tasks.update_one({"_id": task_id}, {"$set": {"task_description": new_text}})
    return redirect(url_for("tasks.index", date=date_str))

# when a user marks a task as complete
@pages.post("/complete")
def complete():
    date_str = request.form.get("date")
    date = datetime.datetime.fromisoformat(date_str)

    # FK = "task_id"
    task = request.form.get("task_id")

    # save to completions collection database
    current_app.db.completions.insert_one({"date": date, "task_id": task})
    return redirect(url_for("tasks.index", date=date_str))

# when a user marks a task from complete to incomplete
@pages.post("/incomplete")
def incomplete():
    date_str = request.form.get("date")
    date = datetime.datetime.fromisoformat(date_str)
    task = request.form.get("task_id")

    # remove from completions collection database
    current_app.db.completions.delete_one({"date": date, "task_id": task})
    return redirect(url_for("tasks.index", date=date_str))

# when a user edits/removes a task
@pages.post("/task_action")
def task_action():
    date_str = request.form.get("date")
    date = datetime.datetime.fromisoformat(date_str)
    task = request.form.get("task_id")

    action = request.form.get("action")
    # if remove button is pressed
    if action == "remove":
        # remove from completions collection database if exists
        if current_app.db.completions.find_one({"date": date, "task_id": task}):
            current_app.db.completions.delete_one({"date": date, "task_id": task})
        current_app.db.tasks.delete_one({"date": date, "_id": task})
        return redirect(url_for("tasks.index", date=date_str))

    if action == "edit":
        element = current_app.db.tasks.find_one({"_id": task})
        old_text = element["task_description"] if element else ""
        return render_template("update_task.html", selected_date=date, task_id=task, task_description=old_text)

    return redirect(url_for("tasks.index"))

