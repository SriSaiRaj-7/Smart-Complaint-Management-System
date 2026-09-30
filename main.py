"""Tkinter desktop entry point for the Smart Complaint Management System."""

from __future__ import annotations

import math
import tkinter as tk
from tkinter import messagebox, ttk

from db import ComplaintDatabase
from models import Complaint
from services.complaint_service import ComplaintService


class ComplaintApp:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.database = ComplaintDatabase()
        self.service = ComplaintService(self.database)

        root.title("Smart Complaint Management System")
        root.geometry("1080x620")
        root.minsize(800, 460)
        root.protocol("WM_DELETE_WINDOW", self.close)

        self._build_main_window()
        self.refresh_complaints()

    def _build_main_window(self) -> None:
        page = ttk.Frame(self.root, padding=20)
        page.pack(fill="both", expand=True)
        page.columnconfigure(0, weight=1)
        page.rowconfigure(3, weight=1)

        ttk.Label(
            page,
            text="Smart Complaint Management System",
            font=("Segoe UI", 18, "bold"),
        ).grid(row=0, column=0, sticky="w")
        ttk.Label(
            page,
            text="Complaints are displayed in priority dispatch order.",
            font=("Segoe UI", 10),
        ).grid(row=1, column=0, sticky="w", pady=(4, 16))

        toolbar = ttk.Frame(page)
        toolbar.grid(row=2, column=0, sticky="ew", pady=(0, 12))
        # Submits to the category hash map via service.raise_complaint().
        ttk.Button(
            toolbar, text="Raise Complaint", command=self.open_raise_dialog
        ).pack(side="left", padx=(0, 8))
        # Rebuilds the heap-ordered list through service.all_by_priority().
        ttk.Button(toolbar, text="View All", command=self.view_all).pack(
            side="left", padx=(0, 8)
        )
        # Dispatches from the priority heap through service.resolve_next().
        ttk.Button(
            toolbar, text="Resolve Next", command=self.resolve_next
        ).pack(side="left")
        # Searches the service hash-map indexes by complaint ID or category.
        ttk.Button(
            toolbar, text="Search", command=self.open_search_dialog
        ).pack(side="left", padx=(8, 0))
        # Opens the escalation chain view and simulated-time controls.
        ttk.Button(
            toolbar, text="Escalation", command=self.open_escalation_window
        ).pack(side="left", padx=(8, 0))
        # Opens the newest-first audit stack for a selected complaint.
        ttk.Button(
            toolbar, text="Audit Trail", command=self.open_audit_dialog
        ).pack(side="left", padx=(8, 0))
        # Displays the category/status aggregates and average resolution time.
        ttk.Button(toolbar, text="Stats", command=self.open_stats_window).pack(
            side="left", padx=(8, 0)
        )

        table_frame = ttk.Frame(page)
        table_frame.grid(row=3, column=0, sticky="nsew")
        table_frame.rowconfigure(0, weight=1)
        table_frame.columnconfigure(0, weight=1)

        columns = ("id", "title", "category", "priority", "status", "level")
        self.table = ttk.Treeview(
            table_frame, columns=columns, show="headings", height=18
        )
        headings = (
            ("id", "ID", 70),
            ("title", "Title", 340),
            ("category", "Category", 130),
            ("priority", "Priority score", 130),
            ("status", "Status", 140),
            ("level", "Escalation level", 130),
        )
        for column, label, width in headings:
            self.table.heading(column, text=label)
            self.table.column(column, width=width, minwidth=60, anchor="w")
        self.table.grid(row=0, column=0, sticky="nsew")

        scrollbar = ttk.Scrollbar(
            table_frame, orient="vertical", command=self.table.yview
        )
        scrollbar.grid(row=0, column=1, sticky="ns")
        self.table.configure(yscrollcommand=scrollbar.set)

    def refresh_complaints(self) -> None:
        for item in self.table.get_children():
            self.table.delete(item)
        for complaint in self.service.all_by_priority():
            self.table.insert(
                "",
                "end",
                values=(
                    complaint.id,
                    complaint.title,
                    complaint.category.title(),
                    f"{complaint.priority_score:.2f}",
                    complaint.status.replace("_", " ").title(),
                    complaint.escalation_level,
                ),
            )

    def view_all(self) -> None:
        # Rebuilds the priority heap view through service.all_by_priority().
        self.refresh_complaints()

    def open_raise_dialog(self) -> None:
        # Opens the entry form for service.raise_complaint() and category indexing.
        dialog = tk.Toplevel(self.root)
        dialog.title("Raise Complaint")
        dialog.transient(self.root)
        dialog.grab_set()
        dialog.resizable(False, False)

        form = ttk.Frame(dialog, padding=18)
        form.grid(sticky="nsew")
        form.columnconfigure(1, weight=1)

        ttk.Label(form, text="Title").grid(row=0, column=0, sticky="w", pady=5)
        title_entry = ttk.Entry(form, width=44)
        title_entry.grid(row=0, column=1, sticky="ew", pady=5)

        ttk.Label(form, text="Description").grid(
            row=1, column=0, sticky="nw", pady=5
        )
        description_entry = tk.Text(form, width=44, height=5, wrap="word")
        description_entry.grid(row=1, column=1, sticky="ew", pady=5)

        ttk.Label(form, text="Category").grid(row=2, column=0, sticky="w", pady=5)
        category_box = ttk.Combobox(
            form,
            values=("electrical", "plumbing", "academic", "hostel", "other"),
            state="readonly",
        )
        category_box.grid(row=2, column=1, sticky="ew", pady=5)
        category_box.current(0)

        ttk.Label(form, text="Raised by").grid(row=3, column=0, sticky="w", pady=5)
        raised_by_entry = ttk.Entry(form, width=44)
        raised_by_entry.grid(row=3, column=1, sticky="ew", pady=5)

        ttk.Label(form, text="Urgency (1-5)").grid(
            row=4, column=0, sticky="w", pady=5
        )
        urgency_box = ttk.Spinbox(form, from_=1, to=5, width=8)
        urgency_box.set("3")
        urgency_box.grid(row=4, column=1, sticky="w", pady=5)

        def submit() -> None:
            try:
                urgency = int(urgency_box.get())
                # Uses service.raise_complaint() to enforce validation, scoring, and duplicates.
                complaint = self.service.raise_complaint(
                    title_entry.get(),
                    description_entry.get("1.0", "end").strip(),
                    category_box.get(),
                    raised_by_entry.get(),
                    urgency,
                )
            except (ValueError, KeyError) as error:
                self.refresh_complaints()
                messagebox.showerror("Could not raise complaint", str(error), parent=dialog)
                return
            messagebox.showinfo(
                "Complaint created",
                f"Complaint #{complaint.id} created with priority "
                f"{complaint.priority_score:.2f}.",
                parent=dialog,
            )
            dialog.destroy()
            self.refresh_complaints()

        # Calls the DSA-backed raise handler only after the form fields are collected.
        ttk.Button(form, text="Submit", command=submit).grid(
            row=5, column=1, sticky="e", pady=(12, 0)
        )
        title_entry.focus_set()

    def resolve_next(self) -> None:
        # Pops the next item from the priority heap and same-score FIFO queue.
        complaint = self.service.resolve_next()
        if complaint is None:
            messagebox.showinfo("Resolve next", "There are no unresolved complaints.", parent=self.root)
        else:
            messagebox.showinfo(
                "Complaint resolved",
                f"Resolved complaint #{complaint.id}: {complaint.title}",
                parent=self.root,
            )
        self.refresh_complaints()

    def open_search_dialog(self) -> None:
        # Opens the hash-map lookup dialog for search_by_id/search_by_category.
        dialog = tk.Toplevel(self.root)
        dialog.title("Search Complaints")
        dialog.transient(self.root)
        dialog.grab_set()
        dialog.resizable(False, False)

        form = ttk.Frame(dialog, padding=18)
        form.pack(fill="both", expand=True)
        ttk.Label(form, text="Search by").grid(row=0, column=0, sticky="w", padx=(0, 8))
        search_type = ttk.Combobox(
            form, values=("ID", "Category"), state="readonly", width=14
        )
        search_type.current(0)
        search_type.grid(row=0, column=1, sticky="w")
        query_entry = ttk.Entry(form, width=32)
        query_entry.grid(row=1, column=0, columnspan=2, sticky="ew", pady=(12, 0))
        query_entry.focus_set()

        def search_now() -> None:
            self.refresh_complaints()
            query = query_entry.get().strip()
            if not query:
                messagebox.showerror("Search", "Enter an ID or category.", parent=dialog)
                return
            if search_type.get() == "ID":
                try:
                    complaint_id = int(query)
                    if complaint_id < 1:
                        raise ValueError
                except ValueError:
                    messagebox.showerror(
                        "Search", "Enter a valid positive complaint ID.", parent=dialog
                    )
                    return
                complaint = self.service.search_by_id(complaint_id)
                results = [complaint] if complaint else []
            else:
                category = query.lower()
                if category not in ("electrical", "plumbing", "academic", "hostel", "other"):
                    messagebox.showerror("Search", "Choose a valid category.", parent=dialog)
                    return
                results = self.service.search_by_category(category)

            self.show_complaint_results(f"Search results: {query}", results)
            self.refresh_complaints()

        # Triggers the selected hash-map lookup and renders its returned complaints.
        ttk.Button(form, text="Search", command=search_now).grid(
            row=2, column=1, sticky="e", pady=(12, 0)
        )
        dialog.bind("<Return>", lambda _event: search_now())

    def show_complaint_results(
        self, title: str, complaints: list[Complaint]
    ) -> None:
        window = tk.Toplevel(self.root)
        window.title(title)
        window.geometry("850x340")
        frame = ttk.Frame(window, padding=12)
        frame.pack(fill="both", expand=True)
        columns = ("id", "title", "category", "priority", "status", "level")
        results = ttk.Treeview(frame, columns=columns, show="headings", height=12)
        headings = (
            ("id", "ID", 60),
            ("title", "Title", 300),
            ("category", "Category", 110),
            ("priority", "Priority", 90),
            ("status", "Status", 110),
            ("level", "Level", 70),
        )
        for column, label, width in headings:
            results.heading(column, text=label)
            results.column(column, width=width, anchor="w")
        results.pack(fill="both", expand=True)
        for complaint in complaints:
            results.insert(
                "",
                "end",
                values=(
                    complaint.id,
                    complaint.title,
                    complaint.category.title(),
                    f"{complaint.priority_score:.2f}",
                    complaint.status.replace("_", " ").title(),
                    complaint.escalation_level,
                ),
            )
        if not complaints:
            ttk.Label(frame, text="No matching complaints found.").pack(
                anchor="w", pady=(8, 0)
            )

    def open_escalation_window(self) -> None:
        # Reads escalation status from the service ID map and resolves targets in the escalation chain.
        self.refresh_complaints()
        window = tk.Toplevel(self.root)
        window.title("Escalation")
        window.geometry("860x500")
        window.minsize(700, 380)

        frame = ttk.Frame(window, padding=16)
        frame.pack(fill="both", expand=True)
        frame.columnconfigure(0, weight=1)
        frame.rowconfigure(1, weight=1)

        ttk.Label(
            frame,
            text="Current escalation status",
            font=("Segoe UI", 13, "bold"),
        ).grid(row=0, column=0, sticky="w", pady=(0, 10))

        columns = ("id", "title", "status", "level", "target")
        status_table = ttk.Treeview(
            frame, columns=columns, show="headings", height=12
        )
        for column, label, width in (
            ("id", "ID", 60),
            ("title", "Title", 340),
            ("status", "Status", 140),
            ("level", "Level", 80),
            ("target", "Current target", 140),
        ):
            status_table.heading(column, text=label)
            status_table.column(column, width=width, anchor="w")
        status_table.grid(row=1, column=0, sticky="nsew")
        scrollbar = ttk.Scrollbar(
            frame, orient="vertical", command=status_table.yview
        )
        scrollbar.grid(row=1, column=1, sticky="ns")
        status_table.configure(yscrollcommand=scrollbar.set)

        time_label = ttk.Label(frame, text="Simulated time advanced: 0 hours")
        time_label.grid(row=2, column=0, sticky="w", pady=(10, 0))

        def refresh_status() -> None:
            for item in status_table.get_children():
                status_table.delete(item)
            for complaint in sorted(
                self.service.by_id.values(), key=lambda item: item.id or 0
            ):
                status_table.insert(
                    "",
                    "end",
                    values=(
                        complaint.id,
                        complaint.title,
                        complaint.status.replace("_", " ").title(),
                        complaint.escalation_level,
                        self.service.escalation_target(complaint.escalation_level).title(),
                    ),
                )
            elapsed = self.service.time_offset.total_seconds() / 3600
            time_label.configure(text=f"Simulated time advanced: {elapsed:g} hours")

        controls = ttk.Frame(frame)
        controls.grid(row=3, column=0, columnspan=2, sticky="ew", pady=(12, 0))
        ttk.Label(controls, text="Advance hours:").pack(side="left", padx=(0, 6))
        hours_entry = ttk.Entry(controls, width=10)
        hours_entry.pack(side="left", padx=(0, 8))

        def advance_time() -> None:
            # Calls service.advance_time() while the existing service owns simulated time.
            try:
                hours = float(hours_entry.get())
                if not math.isfinite(hours):
                    raise ValueError("Enter a finite number of hours.")
                self.service.advance_time(hours)
            except (ValueError, OverflowError) as error:
                self.refresh_complaints()
                messagebox.showerror("Invalid time", str(error), parent=window)
                return
            refresh_status()
            self.refresh_complaints()
            messagebox.showinfo(
                "Simulated time", f"Advanced time by {hours:g} hours.", parent=window
            )

        # Advances simulated complaint age through the service escalation timer.
        ttk.Button(controls, text="Advance Time", command=advance_time).pack(
            side="left", padx=(0, 16)
        )

        def check_escalation() -> None:
            # Runs the escalation chain using service.force_escalation_check().
            escalated = self.service.force_escalation_check()
            if escalated:
                details = "\n".join(
                    f"#{item.id} escalated to "
                    f"{self.service.escalation_target(item.escalation_level).title()}"
                    for item in escalated
                )
                messagebox.showinfo("Escalation check", details, parent=window)
            else:
                messagebox.showinfo(
                    "Escalation check",
                    "No complaints require escalation.",
                    parent=window,
                )
            refresh_status()
            self.refresh_complaints()

        # Advances overdue complaints along the escalation chain.
        ttk.Button(
            controls, text="Run Escalation Check", command=check_escalation
        ).pack(side="left")
        refresh_status()

    def open_audit_dialog(self) -> None:
        # Opens an audit-log lookup using service.audit_trail().
        dialog = tk.Toplevel(self.root)
        dialog.title("Audit Trail")
        dialog.geometry("700x420")
        dialog.minsize(520, 320)

        frame = ttk.Frame(dialog, padding=16)
        frame.pack(fill="both", expand=True)
        ttk.Label(frame, text="Complaint ID:").pack(anchor="w")
        id_entry = ttk.Entry(frame, width=18)
        id_entry.pack(anchor="w", pady=(4, 10))
        list_frame = ttk.Frame(frame)
        list_frame.pack(fill="both", expand=True)
        history = tk.Listbox(list_frame, font=("Segoe UI", 10), activestyle="none")
        history.pack(side="left", fill="both", expand=True)
        history_scrollbar = ttk.Scrollbar(
            list_frame, orient="vertical", command=history.yview
        )
        history_scrollbar.pack(side="right", fill="y")
        history.configure(yscrollcommand=history_scrollbar.set)

        def load_audit() -> None:
            # Looks up the complaint and its newest-first audit stack.
            self.refresh_complaints()
            try:
                complaint_id = int(id_entry.get())
                if complaint_id < 1:
                    raise ValueError
            except ValueError:
                messagebox.showerror(
                    "Audit Trail", "Enter a valid positive complaint ID.", parent=dialog
                )
                return
            complaint = self.service.search_by_id(complaint_id)
            if complaint is None:
                messagebox.showerror(
                    "Audit Trail", "Complaint not found.", parent=dialog
                )
                return
            history.delete(0, tk.END)
            for change in self.service.audit_trail(complaint_id):
                history.insert(
                    tk.END,
                    f"{change.changed_at:%Y-%m-%d %H:%M:%S}  "
                    f"{change.old_status.replace('_', ' ')} -> "
                    f"{change.new_status.replace('_', ' ')}  |  {change.note}",
                )
            self.refresh_complaints()
            if history.size() == 0:
                history.insert(tk.END, "No audit entries recorded.")

        # Triggers hash-map ID lookup followed by the audit stack read.
        ttk.Button(frame, text="Load Audit Trail", command=load_audit).pack(
            anchor="e", pady=(10, 0)
        )
        id_entry.focus_set()

    def open_stats_window(self) -> None:
        # Reads category, status, and resolution aggregates from service.stats().
        summary = self.service.stats()
        window = tk.Toplevel(self.root)
        window.title("Complaint Statistics")
        window.geometry("680x430")
        window.minsize(520, 340)

        frame = ttk.Frame(window, padding=18)
        frame.pack(fill="both", expand=True)
        ttk.Label(
            frame,
            text="Complaint Statistics",
            font=("Segoe UI", 16, "bold"),
        ).pack(anchor="w")
        ttk.Label(
            frame,
            text=(
                "Average resolution time: "
                f"{summary['average_resolution_hours']:.2f} hours"
            ),
            font=("Segoe UI", 11),
        ).pack(anchor="w", pady=(6, 18))

        tables = ttk.Frame(frame)
        tables.pack(fill="both", expand=True)
        tables.columnconfigure(0, weight=1)
        tables.columnconfigure(1, weight=1)

        def add_count_table(
            parent: ttk.Frame, column: int, title: str, counts: dict[str, int]
        ) -> None:
            section = ttk.LabelFrame(parent, text=title, padding=10)
            section.grid(row=0, column=column, sticky="nsew", padx=(0, 8) if column == 0 else (8, 0))
            count_table = ttk.Treeview(
                section, columns=("name", "count"), show="headings", height=10
            )
            name_heading = "Category" if title == "Categories" else "Status"
            count_table.heading("name", text=name_heading)
            count_table.heading("count", text="Count")
            count_table.column("name", width=150, anchor="w")
            count_table.column("count", width=70, anchor="center")
            count_table.pack(fill="both", expand=True)
            for name, count in sorted(counts.items()):
                count_table.insert("", "end", values=(name.replace("_", " ").title(), count))
            if not counts:
                count_table.insert("", "end", values=("No data", 0))

        # Shows the per-category totals returned by the service statistics method.
        add_count_table(tables, 0, "Categories", summary["by_category"])
        # Shows the per-status totals returned by the service statistics method.
        add_count_table(tables, 1, "Statuses", summary["by_status"])
        self.refresh_complaints()

    def close(self) -> None:
        self.database.close()
        self.root.destroy()


def main() -> None:
    root = tk.Tk()
    ComplaintApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
