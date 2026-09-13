# Online Course: Django exam assessment

An extension of the [IBM Online Course starter](https://github.com/ibm-developer-skills-network/tfjzl-final-cloud-app-with-database). Learners register, enroll in a course, read its lessons and submit an exam with multiple correct choices. Results show the score and feedback for every answer; learners can retake the exam without replacing previous submissions.

## Run locally or in Skills Network Cloud IDE

Requires Python 3.10 or later. The app has been run in Skills Network Cloud IDE with Python 3.10 and Django 5.2.17. Dependencies are pinned in `requirements.txt`. From the project directory, create a virtual environment:

```bash
python3 -m venv djangoenv
```

If Cloud IDE reports that `ensurepip` is unavailable, use the lab's working fallback:

```bash
python3 -m pip install --user virtualenv
python3 -m virtualenv djangoenv
```

Activate the environment and start the app:

```bash
source djangoenv/bin/activate
python -m pip install -r requirements.txt
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver 0.0.0.0:8000
```

Open `http://127.0.0.1:8000/onlinecourse/` for courses and `/admin/` for the admin site. In Cloud IDE, launch the application on **port 8000** and append `/onlinecourse/` or `/admin/` to its generated URL. Keep the terminal running while using the application.

Use the admin site to create an instructor, a course with lessons and questions, then add each question's choices. [SUBMISSION.md](SUBMISSION.md) describes the required admin workflow and evidence.

For a quick optional demo, stop the server with Ctrl+C and run the command below. Replace `admin` with the username you created, then restart the server.

```bash
python manage.py seed_demo --instructor admin
python manage.py runserver 0.0.0.0:8000
```

The command creates **Learning Django** with two lessons, two questions worth 50 points each, and four choices per question. Each question has two correct answers. It preserves an existing Learning Django course instead of replacing its content. This convenience command does not constitute creating the course through the admin interface.

## How assessment works

- `Question` belongs to a course; `Choice` belongs to a question; `Submission` belongs to an enrollment and stores the selected choices.
- Each question earns all its points only when selected choices exactly match the correct choices. Missing a correct answer or selecting an incorrect one earns zero for that question.
- The percentage is `100 × earned points / available points`. Passing requires **strictly more than 80%**, following the starter's rule. Exactly 80% fails.
- Authentication, enrollment, POST and CSRF protection are required for submissions. Invalid or unrelated choices are rejected. Learners can view only their own results for the requested course.
- A blank attempt is recorded and receives zero. Retaking creates a new submission.

The course template used by the app is `onlinecourse/templates/onlinecourse/course_details_bootstrap.html`. The singular starter filename remains as a compatibility template.

## Developer checks

```bash
python manage.py check
python manage.py makemigrations --check --dry-run
python manage.py test onlinecourse
```

The 13 tests cover exact answer matching, weighted scores and the 80% boundary, blank attempts, retries, authentication and enrollment, private results, invalid choices, CSRF, course lessons, duplicate enrollment and admin creation of course/exam content.

## Lab settings and limits

SQLite stores data in `db.sqlite3`. The default `DJANGO_DEBUG=1` and development server are intended for this lab. `DJANGO_ALLOWED_HOSTS` accepts a comma-separated host list; defaults include local hosts and the Skills Network domains. A local secret is generated automatically; `DJANGO_SECRET_KEY` can supply an environment-specific value. Database files, local secrets, uploaded media and the virtual environment are excluded from source control.

Results use the current question grades and answer definitions. Submissions preserve selected choices, but do not snapshot the original exam: editing or deleting exam content can change how earlier attempts are displayed and scored. A production assessment system would need versioned exams and additional deployment configuration.

See [SUBMISSION.md](SUBMISSION.md) for the seven assessment deliverables and public repository links. Upload the prepared screenshots separately to the assessment.
