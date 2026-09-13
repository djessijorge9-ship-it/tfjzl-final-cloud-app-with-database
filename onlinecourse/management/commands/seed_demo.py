"""Create the optional, repeatable course used to demonstrate exam features."""

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils.timezone import localdate

from onlinecourse.models import Choice, Course, Instructor, Lesson, Question


class Command(BaseCommand):
    help = 'Create the Learning Django demo course without replacing existing content.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--instructor',
            metavar='USERNAME',
            help='Assign an existing user as the demo course instructor.',
        )

    @transaction.atomic
    def handle(self, *args, **options):
        instructor_user = None
        if options['instructor']:
            user_model = get_user_model()
            try:
                instructor_user = user_model.objects.get(
                    **{user_model.USERNAME_FIELD: options['instructor']}
                )
            except user_model.DoesNotExist as exc:
                raise CommandError(
                    f"User {options['instructor']!r} does not exist. "
                    'Create the user first or omit --instructor.'
                ) from exc

        try:
            course, created = Course.objects.get_or_create(
                name='Learning Django',
                defaults={
                    'description': (
                        'Django is an extremely popular and fully featured '
                        'server-side web framework, written in Python'
                    ),
                    'image': '',
                    'pub_date': localdate(),
                },
            )
        except Course.MultipleObjectsReturned as exc:
            raise CommandError(
                'More than one Learning Django course exists. '
                'Rename the duplicate courses before running seed_demo.'
            ) from exc

        if created:
            self.create_content(course)
            self.stdout.write(self.style.SUCCESS(
                f'Created Learning Django (course {course.pk}): '
                '2 lessons, 2 questions, 8 choices, 100 total points.'
            ))
        else:
            self.stdout.write(self.style.WARNING(
                f'Learning Django already exists (course {course.pk}); '
                'its lessons, questions, choices and course fields were preserved.'
            ))

        if instructor_user is not None:
            instructor, _ = Instructor.objects.get_or_create(
                user=instructor_user,
                defaults={'total_learners': 0, 'full_time': True},
            )
            course.instructors.add(instructor)
            self.stdout.write(self.style.SUCCESS(
                f'Assigned instructor {instructor_user.get_username()}.'
            ))

    def create_content(self, course):
        Lesson.objects.create(
            course=course,
            title='What is Django',
            order=0,
            content=(
                'Django is a high-level Python web framework for building web '
                'applications. Its built-in object-relational mapper (ORM) lets '
                'you define models as Python classes and work with database '
                'records through Python objects. Django also provides routing, '
                'templates, authentication and an administration site.'
            ),
        )
        Lesson.objects.create(
            course=course,
            title='Models and exam relationships',
            order=1,
            content=(
                'A ForeignKey represents a many-to-one relationship: many '
                'choices can belong to one question. A ManyToManyField allows '
                'a submission to contain several choices and a choice to '
                'appear in several submissions. Each question in this exam '
                'has two correct answers. Select both correct answers and no '
                'incorrect answers to earn its 50 points.'
            ),
        )

        questions = [
            (
                'Which statements about Django are correct? Select two.',
                [
                    ('Django is a web framework written in Python.', True),
                    ('Django includes an object-relational mapper (ORM).', True),
                    ('Django only serves static HTML files.', False),
                    ('Django requires Oracle as its only database.', False),
                ],
            ),
            (
                'Which model relationships are correct for this exam app? Select two.',
                [
                    ('A Choice has a many-to-one relationship with Question.', True),
                    ('Submission and Choice have a many-to-many relationship.', True),
                    ('Each Course can contain only one Question.', False),
                    ('Each Choice can appear in only one Submission.', False),
                ],
            ),
        ]
        for content, choices in questions:
            question = Question.objects.create(course=course, content=content, grade=50)
            Choice.objects.bulk_create([
                Choice(question=question, content=text, is_correct=correct)
                for text, correct in choices
            ])
