"""Transactions CRUD and CSV import routes."""
import csv
import io
from calendar import monthrange
from datetime import datetime

from flask import flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from app import db
from app.blueprints.transactions import transactions_bp
from app.models import Category, Transaction


def _get_or_create_categories(user_id: int) -> dict:
    """Ensure user has default categories; return name->id mapping."""
    cats = Category.query.filter_by(user_id=user_id).all()
    if not cats:
        for name, t in [
            ("Sales", "income"),
            ("Other Income", "income"),
            ("Rent", "expense"),
            ("Utilities", "expense"),
            ("Supplies", "expense"),
            ("Payroll", "expense"),
            ("Marketing", "expense"),
        ]:
            c = Category(user_id=user_id, name=name, type=t)
            db.session.add(c)
        db.session.commit()
        cats = Category.query.filter_by(user_id=user_id).all()
    return {c.name: c for c in cats}


@transactions_bp.route("/", methods=["GET"])
@login_required
def list_transactions():
    """List transactions with optional filters."""
    q = Transaction.query.filter_by(user_id=current_user.id).order_by(Transaction.date.desc())
    type_filter = request.args.get("type")
    if type_filter in ("income", "expense"):
        q = q.filter_by(type=type_filter)
    month = request.args.get("month")
    if month:
        try:
            start = datetime.strptime(month + "-01", "%Y-%m-%d").date()
            _, last = monthrange(start.year, start.month)
            end = start.replace(day=last)
            q = q.filter(Transaction.date >= start, Transaction.date <= end)
        except ValueError:
            pass
    transactions = q.limit(200).all()
    return render_template("transactions/list.html", transactions=transactions)


@transactions_bp.route("/add", methods=["GET", "POST"])
@login_required
def add():
    """Add a new transaction."""
    categories = Category.query.filter_by(user_id=current_user.id).all()
    if not categories:
        _get_or_create_categories(current_user.id)
        categories = Category.query.filter_by(user_id=current_user.id).all()

    if request.method == "POST":
        try:
            date_str = request.form.get("date")
            amount = float(request.form.get("amount", 0))
            tx_type = request.form.get("type", "expense")
            category_id = request.form.get("category_id") or None
            merchant = (request.form.get("merchant") or "").strip() or None
            notes = (request.form.get("notes") or "").strip() or None

            if not date_str:
                flash("Date is required", "error")
                return render_template("transactions/form.html", categories=categories)

            tx_date = datetime.strptime(date_str, "%Y-%m-%d").date()
            if tx_type == "income":
                amount = abs(amount)
            else:
                amount = -abs(amount) if amount > 0 else amount

            t = Transaction(
                user_id=current_user.id,
                date=tx_date,
                amount=abs(amount),
                type=tx_type,
                category_id=int(category_id) if category_id else None,
                merchant=merchant,
                notes=notes,
            )
            db.session.add(t)
            db.session.commit()
            flash("Transaction added.", "success")
            return redirect(url_for("transactions.list_transactions"))
        except (ValueError, TypeError) as e:
            flash(f"Invalid input: {e}", "error")
    return render_template("transactions/form.html", categories=categories)


@transactions_bp.route("/<int:tx_id>/edit", methods=["GET", "POST"])
@login_required
def edit(tx_id):
    """Edit a transaction."""
    t = Transaction.query.filter_by(id=tx_id, user_id=current_user.id).first_or_404()
    categories = Category.query.filter_by(user_id=current_user.id).all()

    if request.method == "POST":
        try:
            date_str = request.form.get("date")
            amount = float(request.form.get("amount", 0))
            tx_type = request.form.get("type", "expense")
            category_id = request.form.get("category_id") or None
            merchant = (request.form.get("merchant") or "").strip() or None
            notes = (request.form.get("notes") or "").strip() or None

            if not date_str:
                flash("Date is required", "error")
                return render_template("transactions/form.html", transaction=t, categories=categories)

            t.date = datetime.strptime(date_str, "%Y-%m-%d").date()
            t.amount = abs(amount)
            t.type = tx_type
            t.category_id = int(category_id) if category_id else None
            t.merchant = merchant
            t.notes = notes
            db.session.commit()
            flash("Transaction updated.", "success")
            return redirect(url_for("transactions.list_transactions"))
        except (ValueError, TypeError) as e:
            flash(f"Invalid input: {e}", "error")
    return render_template("transactions/form.html", transaction=t, categories=categories)


@transactions_bp.route("/<int:tx_id>/delete", methods=["POST"])
@login_required
def delete(tx_id):
    """Delete a transaction."""
    t = Transaction.query.filter_by(id=tx_id, user_id=current_user.id).first_or_404()
    db.session.delete(t)
    db.session.commit()
    flash("Transaction deleted.", "success")
    return redirect(url_for("transactions.list_transactions"))


@transactions_bp.route("/import", methods=["GET", "POST"])
@login_required
def import_csv():
    """Import transactions from CSV upload."""
    if request.method == "GET":
        return render_template("transactions/import.html")

    file = request.files.get("file")
    if not file or not file.filename.endswith(".csv"):
        flash("Please upload a CSV file.", "error")
        return redirect(url_for("transactions.import_csv"))

    cats = _get_or_create_categories(current_user.id)
    stream = io.StringIO(file.stream.read().decode("utf-8", errors="replace"))
    reader = csv.DictReader(stream)

    # Support formats: date,amount,type,category,merchant,notes
    # Or: date,description,amount (amount sign = income/expense)
    created = 0
    errors = []

    for i, row in enumerate(reader):
        try:
            date_str = row.get("date", "").strip()
            amt_str = row.get("amount", "0").replace(",", "").strip()
            if not date_str or not amt_str:
                continue
            amount = float(amt_str)
            tx_type = row.get("type", "").strip().lower() or ("income" if amount >= 0 else "expense")
            if tx_type not in ("income", "expense"):
                tx_type = "income" if amount >= 0 else "expense"
            amount = abs(amount)
            category_name = (row.get("category", "") or row.get("category_name", "")).strip()
            merchant = (row.get("merchant", "") or row.get("description", "")).strip() or None
            notes = (row.get("notes", "") or "").strip() or None

            tx_date = datetime.strptime(date_str[:10], "%Y-%m-%d").date()
            cat = cats.get(category_name) if category_name else None
            if not cat and category_name:
                for c in cats.values():
                    if c.name.lower() == category_name.lower():
                        cat = c
                        break

            t = Transaction(
                user_id=current_user.id,
                date=tx_date,
                amount=amount,
                type=tx_type,
                category_id=cat.id if cat else None,
                merchant=merchant,
                notes=notes,
            )
            db.session.add(t)
            created += 1
        except (ValueError, KeyError) as e:
            errors.append(f"Row {i + 2}: {e}")

    db.session.commit()
    flash(f"Imported {created} transactions." + (f" {len(errors)} rows skipped." if errors else ""), "success")
    return redirect(url_for("transactions.list_transactions"))
