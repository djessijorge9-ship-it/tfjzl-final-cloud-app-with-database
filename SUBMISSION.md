# Final project submission guide

The AI assessment has seven questions worth 15 points; its passing grade is 70%. This assignment threshold is separate from the application's exam threshold of strictly more than 80%.

The public fork is [djessijorge9-ship-it/tfjzl-final-cloud-app-with-database](https://github.com/djessijorge9-ship-it/tfjzl-final-cloud-app-with-database), using the `main` branch. The prepared screenshots, `03-admin-site.png` and `07-final.png`, were captured from the running application and checked for the required content. The successful result shows `100/100` and detailed feedback for both questions. These images are separate assessment attachments and are not included in this repository.

## Prepare an actual course through Django admin

1. Follow the setup in [README.md](README.md), then log in at `/admin/` with the superuser you created.
2. Under **OnlineCourse → Instructors → Add**, select that user, set Total learners to `0`, and save.
3. Under **Courses → Add**, create **Learning Django** with a description, today's publication date and the instructor. Upload a small PNG or JPEG as the required course image, and add at least one lesson using the lesson inline.
4. On the same course form, add two questions using the question inlines, each worth `50` points, then save. For example, ask which statements about Django are correct and which model relationships this app uses.
5. Under **Questions**, open each question. Add four choices through its choice inlines; mark exactly two as correct and save. The exam becomes available after the questions have valid choices.
6. Return to the admin home page. Capture **`03-admin-site.png`**, showing both **Authentication and Authorization** and **OnlineCourse** with the registered models visible.

The optional `seed_demo --instructor admin` command supplies ready-made data for exploring the app. It does not replace the required action of creating course and exam objects through admin. If the seeded Learning Django course already exists, use a distinct name for the course you create through admin.

## Verify a failed attempt, retry and successful result

1. Open `/onlinecourse/`. Sign up or log in as a learner and select **Enroll in course**.
2. Read the lessons, open **Start Exam**, leave the choices blank and select **Submit exam**. Confirm the result shows failure and `0/100`.
3. Select **Retake Exam**, open the exam, choose both correct choices for each question and submit again. Do not select the incorrect choices.
4. Confirm **Congratulations**, `100/100`, and the per-question answer feedback appear. Capture **`07-final.png`** with the course, congratulations message, score and both questions' detailed results visible. A full-page browser screenshot can include the whole result.

For the optional seeded course, the correct statements are: Django is a web framework written in Python; Django includes an ORM; a Choice has a many-to-one relationship with Question; Submission and Choice have a many-to-many relationship. Select the two applicable statements in each question.

## Answer mapping

For URL questions, paste the public file URL itself. For questions 3 and 7, upload the actual image file.

| Question | Points | Public URL or required file |
|---|---:|---|
| 1 — Question, Choice, Submission models | 3 | https://github.com/djessijorge9-ship-it/tfjzl-final-cloud-app-with-database/blob/main/onlinecourse/models.py |
| 2 — Seven model imports and required admin classes | 3 | https://github.com/djessijorge9-ship-it/tfjzl-final-cloud-app-with-database/blob/main/onlinecourse/admin.py |
| 3 — Admin site sections | 1 | Upload `03-admin-site.png` |
| 4 — Course name, lessons and exam template | 2 | https://github.com/djessijorge9-ship-it/tfjzl-final-cloud-app-with-database/blob/main/onlinecourse/templates/onlinecourse/course_details_bootstrap.html |
| 5 — `submit` and `show_exam_result` views | 2 | https://github.com/djessijorge9-ship-it/tfjzl-final-cloud-app-with-database/blob/main/onlinecourse/views.py |
| 6 — Submission and result routes | 2 | https://github.com/djessijorge9-ship-it/tfjzl-final-cloud-app-with-database/blob/main/onlinecourse/urls.py |
| 7 — Successful exam and detailed results | 2 | Upload `07-final.png` |

Before submitting, open each of the five URLs while signed out and confirm that the completed file is visible. Upload the prepared screenshot files for questions 3 and 7. The assessment accepts PNG, JPG, JPEG, GIF or WEBP, up to 100 MB each.

The peer assessment alternative uses seven screenshots instead: `01-models`, `02-admin-file`, `03-admin-site`, `04-course-details`, `05-views`, `06-urls` and `07-final`, saved as PNG or JPEG.
