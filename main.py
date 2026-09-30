"""Flask web entry point for the Smart Complaint Management System."""

from __future__ import annotations

import math
import os
from datetime import timedelta

from flask import Flask, flash, g, redirect, render_template, request, session, url_for

from db import ComplaintDatabase
from services.complaint_service import ComplaintService

app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "local-development-key")
app.config.setdefault("DATABASE_PATH", "complaints.db")


def get_service() -> ComplaintService:
    if "service" not in g:
        database = ComplaintDatabase(app.config["DATABASE_PATH"])
        g.database = database
        service = ComplaintService(database)
        service.time_offset = timedelta(hours=session.get("time_offset_hours", 0))
        g.service = service
    return g.service


@app.teardown_appcontext
def close_database(_error: BaseException | None = None) -> None:
    database = g.pop("database", None)
    if database is not None:
        database.close()


@app.route("/")
def dashboard():
    # Uses the priority heap and same-score FIFO queues via all_by_priority().
    complaints = get_service().all_by_priority()
    return render_template("dashboard.html", complaints=complaints)


@app.route("/raise", methods=["GET", "POST"])
def raise_complaint():
    # Uses service.raise_complaint() to validate and index a complaint by category.
    categories = ("electrical", "plumbing", "academic", "hostel", "other")
    if request.method == "POST":
        title = request.form.get("title", "").strip()
        description = request.form.get("description", "").strip()
        category = request.form.get("category", "").strip().lower()
        raised_by = request.form.get("raised_by", "").strip()
        try:
            urgency = int(request.form.get("urgency", ""))
        except ValueError:
            urgency = 0

        if category not in categories:
            flash("Choose a valid complaint category.", "error")
        elif urgency not in range(1, 6):
            flash("Urgency must be a whole number from 1 to 5.", "error")
        else:
            try:
                complaint = get_service().raise_complaint(
                    title, description, category, raised_by, urgency
                )
            except ValueError as error:
                flash(str(error), "error")
            else:
                flash(f"Complaint #{complaint.id} was created.", "success")
                return redirect(url_for("dashboard"))

    return render_template("raise.html", categories=categories)


@app.post("/resolve-next")
def resolve_next():
    # Uses the priority heap through service.resolve_next() to dispatch one complaint.
    complaint = get_service().resolve_next()
    if complaint is None:
        flash("There are no unresolved complaints to resolve.", "error")
    else:
        flash(f"Resolved complaint #{complaint.id}: {complaint.title}.", "success")
    return redirect(url_for("dashboard"))


@app.get("/search")
def search():
    # Uses the service hash-map indexes through search_by_id() or search_by_category().
    categories = ("electrical", "plumbing", "academic", "hostel", "other")
    search_type = request.args.get("by", "id")
    query = request.args.get("q", "").strip()
    results = []
    searched = bool(query)

    if query and search_type == "id":
        try:
            complaint_id = int(query)
            if complaint_id < 1:
                raise ValueError
        except ValueError:
            flash("Enter a valid positive complaint ID.", "error")
            searched = False
        else:
            complaint = get_service().search_by_id(complaint_id)
            results = [complaint] if complaint else []
    elif query and search_type == "category":
        category = query.lower()
        if category not in categories:
            flash("Choose a valid complaint category.", "error")
            searched = False
        else:
            results = get_service().search_by_category(category)
    elif query:
        flash("Choose whether to search by ID or category.", "error")
        searched = False

    return render_template(
        "search.html",
        categories=categories,
        results=results,
        search_type=search_type,
        query=query,
        searched=searched,
    )


@app.route("/escalation", methods=["GET", "POST"])
def escalation():
    # Uses by_id and escalation_target(); POST actions call the escalation service methods.
    service = get_service()
    if request.method == "POST":
        action = request.form.get("action")
        if action == "advance":
            try:
                hours = float(request.form.get("hours", ""))
            except ValueError:
                hours = math.nan
            if not math.isfinite(hours) or hours < 0:
                flash("Enter a valid non-negative number of hours.", "error")
            else:
                try:
                    service.advance_time(hours)
                except (OverflowError, ValueError):
                    flash("The requested time advance is too large.", "error")
                else:
                    session["time_offset_hours"] = (
                        session.get("time_offset_hours", 0) + hours
                    )
                    flash(f"Advanced simulated time by {hours:g} hours.", "success")
        elif action == "check":
            escalated = service.force_escalation_check()
            if escalated:
                flash(f"Escalated {len(escalated)} complaint(s).", "success")
            else:
                flash("No complaints currently require escalation.", "success")
        else:
            flash("Choose a valid escalation action.", "error")
        return redirect(url_for("escalation"))

    complaints = sorted(service.by_id.values(), key=lambda complaint: complaint.id or 0)
    return render_template(
        "escalation.html",
        complaints=complaints,
        target_for=service.escalation_target,
        time_offset_hours=session.get("time_offset_hours", 0),
    )


@app.get("/audit/<int:complaint_id>")
def audit(complaint_id: int):
    # Reads the complaint's audit stack through service.audit_trail().
    service = get_service()
    complaint = service.by_id.get(complaint_id)
    if complaint is None:
        flash(f"Complaint #{complaint_id} was not found.", "error")
        return redirect(url_for("dashboard"))
    trail = service.audit_trail(complaint_id)
    return render_template("audit.html", complaint=complaint, trail=trail)


@app.get("/stats")
def stats():
    # Aggregates category, status, and resolution-time data through service.stats().
    summary = get_service().stats()
    return render_template("stats.html", summary=summary)


if __name__ == "__main__":
    app.run(debug=True)
