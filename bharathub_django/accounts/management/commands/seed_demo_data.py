import datetime
import random

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.db import transaction

from accounts.models import EmployeeProfile, EmployerProfile
from candidates.models import CandidateProfile
from employers.models import Job
from jobs.models import JobApplication
from shopping.models import Order, OrderItem, Product
from vendor.models import VendorProfile

# ============================================================================
# accounts/management/commands/seed_demo_data.py
#
# వాడకం:  python manage.py seed_demo_data
#
# ఇది 5 Employee + 5 Employer + 5 Vendor test అకౌంట్లు, వాటికి సంబంధించిన
# Jobs / Products / Orders తో సహా క్రియేట్ చేస్తుంది -- కేవలం seed accounts
# మాత్రమే కాదు, 3 dashboards + Home page నిజంగా DB డేటాతో నిండేలా చేస్తుంది.
#
# ఇది idempotent (safe గా మళ్ళీ మళ్ళీ రన్ చేయొచ్చు) -- ఇంతకుముందు ఈ
# స్క్రిప్ట్ తో క్రియేట్ అయిన యూజర్లు ఉంటే, వాటిని update_or_create తో
# తిరిగి వాడుకుంటుంది (డూప్లికేట్ అకౌంట్లు క్రియేట్ చేయదు).
# ============================================================================

PASSWORD_EMPLOYEE = "Employee@123"
PASSWORD_EMPLOYER = "Employer@123"
PASSWORD_VENDOR = "Vendor@123"

EMPLOYEE_NAMES = ["Ravi Kumar", "Priya Sharma", "Arjun Reddy", "Sneha Rao", "Kiran Babu"]
EMPLOYER_COMPANIES = ["TechNova Solutions", "Skyline Infotech", "BluePeak Systems", "Orbit Software", "Vertex Digital"]
VENDOR_SHOPS = ["ComputerWorld Hyderabad", "OfficePro Supplies", "SecureNet IT Services", "PrintHub Solutions", "CloudGear Traders"]

JOB_TITLES = [
    ("Python Developer", Job.Department.ENGINEERING, "Python, Django, MySQL"),
    ("HR Executive", Job.Department.HR, "Recruitment, Communication, MS Office"),
    ("Digital Marketing Specialist", Job.Department.MARKETING, "SEO, Google Ads, Content"),
]

PRODUCT_CATALOG = [
    ("Dell Latitude Laptop", Product.Category.HARDWARE, Product.Unit.PER_UNIT, 68000),
    ("Kaspersky Business Security", Product.Category.SOFTWARE, Product.Unit.PER_MONTH, 350),
    ("Office Cleaning Service", Product.Category.SERVICE, Product.Unit.PER_MONTH, 5000),
    ("A4 Paper Bundle (500 sheets)", Product.Category.OFFICE_SUPPLY, Product.Unit.PER_UNIT, 350),
    ("Corporate Training Workshop", Product.Category.TRAINING, Product.Unit.FIXED, 25000),
]


class Command(BaseCommand):
    help = "Employee/Employer/Vendor కి చెరో 5 డెమో అకౌంట్లు + Jobs/Products/Orders సీడ్ చేస్తుంది."

    @transaction.atomic
    def handle(self, *args, **options):
        User = get_user_model()
        self.stdout.write(self.style.WARNING("🌱 Seeding demo data..."))

        # ── EMPLOYEES ────────────────────────────────────────────────
        employees = []
        for i, name in enumerate(EMPLOYEE_NAMES, start=1):
            username = f"emp{i}"
            first, last = (name.split() + [""])[:2]
            user, _ = User.objects.update_or_create(
                username=username,
                defaults={"email": f"{username}@bharathub-demo.com", "first_name": first, "last_name": last},
            )
            user.set_password(PASSWORD_EMPLOYEE)
            user.save()

            EmployeeProfile.objects.update_or_create(
                user=user,
                defaults={
                    "mobile_number": f"90000000{i:02d}",
                    "date_of_birth": datetime.date(1995 + i, (i % 12) + 1, 10),
                    "gender": EmployeeProfile.Gender.MALE if i % 2 else EmployeeProfile.Gender.FEMALE,
                    "marital_status": EmployeeProfile.MaritalStatus.UNMARRIED,
                    "father_name": f"Father of {name}",
                },
            )
            CandidateProfile.objects.update_or_create(
                user=user,
                defaults={
                    "headline": f"{JOB_TITLES[i % 3][0]} · Fresher",
                    "location": "Hyderabad",
                    "skills": JOB_TITLES[i % 3][2],
                    "qualification": "B.Tech",
                    "experience_level": CandidateProfile.ExperienceLevel.FRESHER,
                    "hire_status": CandidateProfile.HireStatus.AVAILABLE,
                },
            )
            employees.append(user)
            self.stdout.write(f"  👤 Employee: {username} / {PASSWORD_EMPLOYEE}  ({name})")

        # ── EMPLOYERS + JOBS ─────────────────────────────────────────
        employer_profiles = []
        for i, company in enumerate(EMPLOYER_COMPANIES, start=1):
            username = f"employer{i}"
            user, _ = User.objects.update_or_create(
                username=username,
                defaults={"email": f"{username}@bharathub-demo.com", "first_name": company},
            )
            user.set_password(PASSWORD_EMPLOYER)
            user.save()

            profile, _ = EmployerProfile.objects.update_or_create(
                user=user,
                defaults={
                    "company_name": company,
                    "corporate_email": f"hr@{username}.com",
                    "pan_number": f"ABCDE{1000+i}F",
                    "industry_sector": "Information Technology",
                    "hq_state": "Telangana",
                },
            )
            employer_profiles.append(profile)

            for title, dept, skills in JOB_TITLES[:2]:
                Job.objects.update_or_create(
                    employer=profile, title=title,
                    defaults={
                        "department": dept,
                        "job_type": Job.JobType.FULL_TIME,
                        "experience_level": Job.ExperienceLevel.FRESHER,
                        "location": "Hyderabad",
                        "salary_min": 3, "salary_max": 6,
                        "description": f"{company} is hiring a {title}. Great growth opportunity.",
                        "skills_required": skills,
                        "openings_count": random.randint(1, 5),
                        "qualification": Job.Qualification.ANY_GRADUATE,
                        "status": Job.Status.ACTIVE,
                    },
                )
            self.stdout.write(f"  🏢 Employer: {username} / {PASSWORD_EMPLOYER}  ({company})")

        # ── JOB APPLICATIONS (candidate ⇄ employer messaging కి కావాలి) ─
        # ప్రతి employer యొక్క మొదటి job కి, ఇద్దరు employees apply
        # చేసినట్టు seed చేస్తాం -- దీనివల్లే messaging యాప్ లో
        # candidate <-> employer చాట్ మొదలుపెట్టడానికి కనీసం ఒక legit
        # సంబంధం ఉంటుంది (messaging/permissions.py చూడండి).
        all_jobs = list(Job.objects.filter(employer__in=employer_profiles))
        for i, employee_user in enumerate(employees):
            if not all_jobs:
                break
            job = all_jobs[i % len(all_jobs)]
            JobApplication.objects.get_or_create(
                job=job, candidate=employee_user.candidate_profile,
                defaults={"cover_note": f"{employee_user.first_name} is interested in this role."},
            )
        self.stdout.write("  📨 Seeded demo job applications (for candidate↔employer messaging).")

        # ── VENDORS + PRODUCTS + ORDERS ──────────────────────────────
        now = datetime.datetime.now(datetime.timezone.utc)
        for i, shop in enumerate(VENDOR_SHOPS, start=1):
            username = f"vendor{i}"
            user, _ = User.objects.update_or_create(
                username=username,
                defaults={"email": f"{username}@bharathub-demo.com", "first_name": shop},
            )
            user.set_password(PASSWORD_VENDOR)
            user.save()

            vendor, _ = VendorProfile.objects.update_or_create(
                user=user,
                defaults={
                    "shop_name": shop,
                    "vendor_email": f"{username}@bharathub-demo.com",
                    "vendor_mobile": f"80000000{i:02d}",
                    "category": "IT & Office Solutions",
                    "working_days": "Mon-Sat",
                },
            )
            self.stdout.write(f"  🛍️ Vendor: {username} / {PASSWORD_VENDOR}  ({shop})")

            products = []
            for name, category, unit, price in PRODUCT_CATALOG:
                product, _ = Product.objects.update_or_create(
                    vendor=vendor, name=name,
                    defaults={
                        "category": category, "unit": unit, "price": price,
                        "stock": random.randint(10, 200), "is_published": True,
                        "description": f"{name} — supplied by {shop}.",
                    },
                )
                products.append(product)

            # ప్రతి వెండర్ కి 6 sample orders (గత 6 నెలల్లో వ్యాపించి),
            # దాదాపు అన్నీ 'delivered' (revenue chart లో కనిపించడానికి),
            # కొన్ని 'processing'/'new'/'cancelled' (donut chart variety కోసం).
            statuses = [Order.Status.DELIVERED, Order.Status.DELIVERED, Order.Status.DELIVERED,
                        Order.Status.PROCESSING, Order.Status.NEW, Order.Status.CANCELLED]
            # ఇంతకుముందు ఈ వెండర్ కి seed చేసిన ఆర్డర్లు ఉంటే, డూప్లికేట్
            # అవ్వకుండా ముందు తీసేసి మళ్ళీ తాజాగా క్రియేట్ చేస్తాం.
            Order.objects.filter(vendor=vendor).delete()
            for j, status in enumerate(statuses):
                buyer = employer_profiles[(i + j) % len(employer_profiles)]
                order = Order.objects.create(vendor=vendor, buyer=buyer, status=status, total_amount=0)
                chosen = random.sample(products, k=min(2, len(products)))
                total = 0
                for product in chosen:
                    qty = random.randint(1, 5)
                    OrderItem.objects.create(order=order, product=product, quantity=qty, price_at_order=product.price)
                    total += product.price * qty
                order.total_amount = total
                order.save(update_fields=["total_amount"])

                # created_at ని గత 6 నెలల్లో వ్యాపింపజేయడానికి, auto_now_add
                # ఉన్నా queryset.update() ద్వారా override చేయొచ్చు.
                months_ago = j
                backdated = now - datetime.timedelta(days=30 * months_ago + random.randint(0, 20))
                Order.objects.filter(pk=order.pk).update(created_at=backdated)

        self.stdout.write(self.style.SUCCESS("\n✅ Seed పూర్తయింది! పైన ఉన్న అకౌంట్లతో login చేయండి."))
