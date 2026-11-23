import argparse
import getpass
import json
import os
import smtplib
import time
from email.message import EmailMessage
from pathlib import Path
from sqlalchemy import select, delete
from sqlalchemy.orm import Session
from .db import engine_for, now, uid
from .models import *
from .schemas import SettingsInput, Register
from .security import hash_password
from .checkout import expire_orders, audit


def seed(db):
    if db.scalar(select(Product.id).limit(1)):
        return
    for name in ("Men", "Women"):
        db.add(Category(id=name.lower(), name=name, slug=name.lower()))
    for slug, name in [
        ("new", "New arrivals"),
        ("everyday", "Everyday essentials"),
        ("oversized", "Room to breathe"),
    ]:
        db.add(Collection(id=slug, slug=slug, name=name))
    db.add(Setting(key="store", value=SettingsInput().model_dump()))
    db.flush()
    source = json.loads(
        (Path(__file__).resolve().parents[2] / "mock_store/catalog.json").read_text()
    )
    prices = {"M01": 49900, "W01": 59900, "M02": 69900, "W02": 59900}
    for p in source["products"]:
        product = Product(
            id=p["id"],
            name=p["name"],
            slug=p["name"].lower().replace(" ", "-"),
            description=p["note"]
            + " Demonstration design; fabric and specifications are not final.",
            category_id=p["audience"].lower(),
            status="published",
            care="Sample care: cold gentle wash, dry in shade. Confirm against the final garment label.",
            size_guide="Sample garment chest: S 96 cm · M 102 cm · L 108 cm · XL 114 cm. Measurements are provisional.",
            seo_title=p["name"] + " | Uyaras",
        )
        db.add(product)
        db.flush()
        for i, (colour, _) in enumerate(p["colours"]):
            db.add(
                Media(
                    product_id=p["id"],
                    url=f"/art/{p['id']}-{colour.lower()}.webp",
                    alt=f"{p['name']} in {colour} — sample illustration",
                    position=i,
                )
            )
            for size in source["sizes"]:
                sku = f"{p['id']}-{colour}-{size}".upper()
                db.add(
                    Variant(
                        sku=sku,
                        product_id=p["id"],
                        size=size,
                        colour=colour,
                        price=prices[p["id"]],
                    )
                )
                db.flush()
                db.add(Inventory(sku=sku, on_hand=0, real_stock=False))
        db.add(ProductCollection(product_id=p["id"], collection_id="new"))
        db.add(
            ProductCollection(
                product_id=p["id"],
                collection_id="oversized" if p["id"] == "M02" else "everyday",
            )
        )
    db.add(
        DeliveryRule(
            pin="500001", name="Hyderabad — TEST ONLY", cod=True, verified=False
        )
    )
    db.add(
        DeliveryRule(
            pin="520001", name="Vijayawada — TEST ONLY", cod=True, verified=False
        )
    )
    db.add(Promotion(code="WELCOME10", percent=10, minimum=99900, limit=100))


def worker(engine, once=False):
    while True:
        with Session(engine) as db, db.begin():
            expire_orders(db)
            db.execute(delete(LoginSession).where(LoginSession.expires < now()))
            db.execute(delete(ResetToken).where(ResetToken.expires < now()))
            db.execute(delete(RateLimit).where(RateLimit.expires < now()))
        # With no SMTP account configured, messages remain queued rather than pretending delivery.
        if os.getenv("SMTP_HOST"):
            with Session(engine) as db, db.begin():
                jobs = db.scalars(
                    select(Outbox)
                    .where(
                        Outbox.status.in_(["pending", "retry", "sending"]),
                        Outbox.available <= now(),
                        Outbox.attempts < 8,
                        Outbox.channel == "email",
                    )
                    .order_by(Outbox.available)
                    .with_for_update(skip_locked=True)
                    .limit(10)
                ).all()
                ids = []
                for job in jobs:
                    job.status = "sending"
                    job.attempts += 1
                    job.available = now() + 300
                    ids.append(job.id)
            for job_id in ids:
                with Session(engine) as db:
                    job = db.get(Outbox, job_id)
                    u = db.get(User, job.user_id)
                    message = EmailMessage()
                    message["From"] = os.environ["SMTP_FROM"]
                    message["To"] = u.email
                    message["Subject"] = job.subject
                    message["Message-ID"] = f"<{job.id}@uyaras.local>"
                    message.set_content(job.message)
                    try:
                        with smtplib.SMTP(
                            os.environ["SMTP_HOST"],
                            int(os.getenv("SMTP_PORT", "587")),
                            timeout=20,
                        ) as smtp:
                            smtp.starttls()
                            if os.getenv("SMTP_USER"):
                                smtp.login(
                                    os.environ["SMTP_USER"], os.environ["SMTP_PASSWORD"]
                                )
                            smtp.send_message(message)
                        job.status = "sent"
                        job.message = "Delivered account notification"
                    except (OSError, smtplib.SMTPException):
                        job.status = "failed" if job.attempts >= 8 else "retry"
                        job.available = now() + min(3600, 30 * 2**job.attempts)
                    db.commit()
        if once:
            return
        time.sleep(15)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "command",
        choices=[
            "seed",
            "demo-stock",
            "owner",
            "worker",
            "worker-once",
            "recovery-link",
        ],
    )
    parser.add_argument("--email")
    args = parser.parse_args()
    engine = engine_for()
    if args.command.startswith("worker"):
        return worker(engine, args.command == "worker-once")
    with Session(engine) as db, db.begin():
        if args.command == "seed":
            seed(db)
            print(
                "Sample catalog seeded. Real inventory remains zero; production ordering disabled."
            )
        elif args.command == "demo-stock":
            if os.getenv("APP_ENV", "development") == "production":
                raise RuntimeError("Cannot add demo stock in production.")
            for row in db.scalars(select(Inventory).with_for_update()):
                if row.real_stock:
                    raise RuntimeError("Refusing to mix real and demo inventory.")
                delta = max(0, 10 - row.on_hand)
                row.on_hand += delta
                if delta:
                    db.add(
                        Movement(
                            sku=row.sku,
                            delta=delta,
                            reason="Explicit development simulation stock",
                            actor="setup",
                        )
                    )
            print("Development-only simulation stock added. It is not real inventory.")
        elif args.command == "owner":
            email = args.email or input("Owner email: ")
            password = getpass.getpass("Owner password (12+ characters): ")
            valid = Register(email=email, password=password, name="Uyaras owner")
            if db.scalar(select(User).where(User.email == valid.email.lower())):
                raise ValueError("Email already exists; no role changed.")
            u = User(
                id=uid(),
                email=valid.email.lower(),
                password=hash_password(password),
                name=valid.name,
                role="Owner",
            )
            db.add(u)
            audit(db, "setup", "owner_created", u.id)
            print("Owner created.")
        elif args.command == "recovery-link":
            if os.getenv("APP_ENV", "development") == "production":
                raise RuntimeError("Development command disabled in production.")
            u = db.scalar(select(User).where(User.email == (args.email or "").lower()))
            if not u:
                raise ValueError("Account not found.")
            job = db.scalar(
                select(Outbox)
                .where(
                    Outbox.user_id == u.id, Outbox.message.like("Reset your Uyaras%")
                )
                .order_by(Outbox.available.desc())
                .limit(1)
            )
            print(job.message if job else "Request password recovery first.")


if __name__ == "__main__":
    main()
