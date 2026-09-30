from db import ComplaintDatabase
from services.complaint_service import ComplaintService


def main() -> None:
    database = ComplaintDatabase()
    try:
        service = ComplaintService(database)
        complaint_data = [
            (
                "Projector not working in Room 204",
                (
                    "The projector in the seminar hall has stopped turning on. "
                    "Classes scheduled today need it for presentations."
                ),
                "academic",
                "Student2",
                2,
            ),
            (
                "Sparking wire near Block C entrance",
                (
                    "A loose wire near the Block C main entrance is sparking "
                    "intermittently. Safety risk, especially at night."
                ),
                "electrical",
                "Student3",
                5,
            ),
            (
                "Broken window latch in Room 108",
                (
                    "The window latch in Room 108 is broken, window won't stay "
                    "shut at night. Security and cold air concern."
                ),
                "hostel",
                "Student5",
                2,
            ),
            (
                "Library Wi-Fi not working",
                (
                    "Wi-Fi in the library reading hall has been down for two "
                    "days, students can't access online resources for assignments."
                ),
                "academic",
                "Student6",
                3,
            ),
            (
                "Corridor lights not turning on",
                (
                    "The corridor lights on the third floor haven't turned on "
                    "for three nights, students walking in the dark."
                ),
                "electrical",
                "Student7",
                4,
            ),
            (
                "Mess food quality complaint",
                (
                    "Food served in the mess for the past week has been "
                    "undercooked on multiple occasions. Multiple students affected."
                ),
                "other",
                "Student8",
                3,
            ),
            (
                "Common room TV remote missing",
                (
                    "The remote for the common room TV has been missing for a "
                    "week, TV can't be used properly."
                ),
                "hostel",
                "Student9",
                1,
            ),
        ]

        for title, description, category, raised_by, urgency in complaint_data:
            already_seeded = any(
                complaint.title.casefold() == title.casefold()
                and complaint.raised_by.casefold() == raised_by.casefold()
                for complaint in service.by_id.values()
            )
            if service.is_duplicate(title, raised_by) or already_seeded:
                continue
            complaint = service.raise_complaint(
                title, description, category, raised_by, urgency
            )
            print(
                f"Complaint id={complaint.id}, "
                f"priority_score={complaint.priority_score:.4f}"
            )
    finally:
        database.close()


if __name__ == "__main__":
    main()