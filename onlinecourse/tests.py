"""Exercise the exam workflow through Django's HTTP and admin interfaces."""

import tempfile

from django.contrib import admin
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import IntegrityError, transaction
from django.test import Client, TestCase, override_settings
from django.urls import reverse

from .models import Choice, Course, Enrollment, Instructor, Lesson, Question, Submission


@override_settings(PASSWORD_HASHERS=['django.contrib.auth.hashers.MD5PasswordHasher'])
class ExamWorkflowTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.learner = get_user_model().objects.create_user('learner', password='Exam-tests-123!')
        cls.other_learner = get_user_model().objects.create_user('other-learner')
        cls.course = Course.objects.create(name='Django exams', description='Exam integration test')
        cls.other_course = Course.objects.create(name='Other course', description='Separate course')
        cls.enrollment = Enrollment.objects.create(user=cls.learner, course=cls.course)
        Lesson.objects.create(course=cls.course, title='First lesson', order=1, content='First content')
        Lesson.objects.create(course=cls.course, title='Second lesson', order=2, content='Second content')
        cls.q1 = Question.objects.create(course=cls.course, content='Select both correct choices', grade=40)
        cls.q2 = Question.objects.create(course=cls.course, content='Choose the correct choice', grade=10)
        cls.a = Choice.objects.create(question=cls.q1, content='Correct A', is_correct=True)
        cls.b = Choice.objects.create(question=cls.q1, content='Correct B', is_correct=True)
        cls.c = Choice.objects.create(question=cls.q1, content='Incorrect C')
        cls.d = Choice.objects.create(question=cls.q2, content='Correct D', is_correct=True)
        cls.e = Choice.objects.create(question=cls.q2, content='Incorrect E')
        foreign_question = Question.objects.create(course=cls.other_course, content='Another exam')
        cls.foreign_choice = Choice.objects.create(question=foreign_question, content='Other answer', is_correct=True)

    def setUp(self):
        self.client.force_login(self.learner)
        self.submit_url = reverse('onlinecourse:submit', args=[self.course.pk])
        self.details_url = reverse('onlinecourse:course_details', args=[self.course.pk])

    def submit_answers(self, *choices):
        response = self.client.post(self.submit_url, {f'choice_{choice.pk}': str(choice.pk) for choice in choices})
        self.assertEqual(response.status_code, 302)
        submission = Submission.objects.latest('pk')
        result_url = reverse('onlinecourse:exam_result', args=[self.course.pk, submission.pk])
        self.assertRedirects(response, result_url, fetch_redirect_response=False)
        result = self.client.get(result_url)
        self.assertEqual(result.status_code, 200)
        return submission, result

    def test_exact_set_scoring_ignores_answers_to_other_questions(self):
        self.assertTrue(self.q1.is_get_score([str(self.a.pk), self.b.pk, self.d.pk]))
        self.assertFalse(self.q1.is_get_score([self.a.pk, self.d.pk]))
        self.assertFalse(self.q1.is_get_score([self.a.pk, self.b.pk, self.c.pk]))
        self.assertFalse(self.q1.is_get_score([]))
        unconfigured = Question.objects.create(course=self.course, content='No correct answer yet')
        Choice.objects.create(question=unconfigured, content='Not correct')
        self.assertFalse(unconfigured.is_get_score([]))

    def test_complete_correct_exam_passes_and_records_all_selected_choices(self):
        submission, response = self.submit_answers(self.a, self.b, self.d)
        self.assertSetEqual(set(submission.choices.values_list('pk', flat=True)), {self.a.pk, self.b.pk, self.d.pk})
        self.assertEqual(response.context['total_score'], 50)
        self.assertEqual(response.context['max_score'], 50)
        self.assertEqual(response.context['grade'], 100)
        self.assertIs(response.context['passed'], True)
        self.assertEqual(len(response.context['question_results']), 2)
        self.assertTemplateUsed(response, 'onlinecourse/exam_result_bootstrap.html')

    def test_partial_multi_select_and_selecting_every_choice_do_not_pass(self):
        _, partial = self.submit_answers(self.a, self.d)
        self.assertEqual(partial.context['grade'], 20)
        self.assertIs(partial.context['passed'], False)
        _, all_choices = self.submit_answers(self.a, self.b, self.c, self.d, self.e)
        self.assertEqual(all_choices.context['grade'], 0)
        self.assertIs(all_choices.context['passed'], False)

    def test_blank_attempt_is_saved_and_scores_zero(self):
        submission, response = self.submit_answers()
        self.assertFalse(submission.choices.exists())
        self.assertEqual(response.context['grade'], 0)
        self.assertIs(response.context['passed'], False)

    def test_weighted_grade_uses_possible_points_and_requires_more_than_80_percent(self):
        _, response = self.submit_answers(self.a, self.b)
        self.assertEqual(response.context['total_score'], 40)
        self.assertEqual(response.context['max_score'], 50)
        self.assertEqual(response.context['grade'], 80)
        self.assertIs(response.context['passed'], False)

    def test_retaking_exam_preserves_first_attempt(self):
        first, _ = self.submit_answers(self.a, self.b, self.d)
        second, response = self.submit_answers(self.c, self.e)
        self.assertNotEqual(first.pk, second.pk)
        self.assertEqual(Submission.objects.filter(enrollment=self.enrollment).count(), 2)
        self.assertEqual(response.context['grade'], 0)
        original = self.client.get(reverse('onlinecourse:exam_result', args=[self.course.pk, first.pk]))
        self.assertEqual(original.context['grade'], 100)
        self.assertSetEqual(set(first.choices.values_list('pk', flat=True)), {self.a.pk, self.b.pk, self.d.pk})

    def test_authentication_enrollment_and_post_are_required(self):
        self.assertEqual(self.client.get(self.submit_url).status_code, 405)
        self.client.logout()
        response = self.client.post(self.submit_url, {f'choice_{self.a.pk}': self.a.pk})
        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse('onlinecourse:login'), response.url)
        self.client.force_login(self.other_learner)
        self.assertIn(self.client.post(self.submit_url).status_code, (403, 404))
        self.assertFalse(Submission.objects.exists())

    def test_results_are_private_and_bound_to_the_course(self):
        submission, _ = self.submit_answers(self.a, self.b, self.d)
        result_url = reverse('onlinecourse:exam_result', args=[self.course.pk, submission.pk])
        self.client.force_login(self.other_learner)
        Enrollment.objects.create(user=self.other_learner, course=self.course)
        self.assertEqual(self.client.get(result_url).status_code, 404)
        self.client.force_login(self.learner)
        wrong_course = reverse('onlinecourse:exam_result', args=[self.other_course.pk, submission.pk])
        self.assertEqual(self.client.get(wrong_course).status_code, 404)
        self.client.logout()
        self.assertEqual(self.client.get(result_url).status_code, 302)

    def test_invalid_or_foreign_choices_are_rejected_without_partial_writes(self):
        invalid_payloads = [
            {f'choice_{self.a.pk}': 'not-an-integer'},
            {'choice_999999999': '999999999'},
            {f'choice_{self.a.pk}': str(self.a.pk), f'choice_{self.foreign_choice.pk}': str(self.foreign_choice.pk)},
        ]
        for payload in invalid_payloads:
            with self.subTest(payload=payload):
                self.assertEqual(self.client.post(self.submit_url, payload).status_code, 400)
                self.assertFalse(Submission.objects.exists())

    def test_csrf_protection_rejects_missing_token_and_accepts_real_form_token(self):
        browser = Client(enforce_csrf_checks=True)
        browser.force_login(self.learner)
        page = browser.get(self.details_url)
        self.assertEqual(page.status_code, 200)
        payload = {f'choice_{choice.pk}': str(choice.pk) for choice in (self.a, self.b, self.d)}
        self.assertEqual(browser.post(self.submit_url, payload).status_code, 403)
        self.assertFalse(Submission.objects.exists())
        payload['csrfmiddlewaretoken'] = browser.cookies['csrftoken'].value
        self.assertEqual(browser.post(self.submit_url, payload).status_code, 302)
        self.assertEqual(Submission.objects.count(), 1)

    def test_details_show_every_lesson_and_gate_exam_by_enrollment(self):
        response = self.client.get(self.details_url)
        self.assertContains(response, 'First content')
        self.assertContains(response, 'Second content')
        self.assertContains(response, self.q1.content)
        self.assertContains(response, self.q2.content)
        self.assertContains(response, f'choice_{self.a.pk}')
        self.assertIs(response.context['is_enrolled'], True)
        self.assertIs(response.context['exam_ready'], True)
        self.client.force_login(self.other_learner)
        response = self.client.get(self.details_url)
        self.assertIs(response.context['is_enrolled'], False)
        self.assertNotContains(response, f'choice_{self.a.pk}')

    def test_duplicate_enrollment_is_prevented_by_database(self):
        with self.assertRaises(IntegrityError), transaction.atomic():
            Enrollment.objects.create(user=self.learner, course=self.course)


@override_settings(PASSWORD_HASHERS=['django.contrib.auth.hashers.MD5PasswordHasher'])
class AdminExamAuthoringTests(TestCase):
    def test_admin_can_create_course_lessons_questions_and_choices(self):
        for model in (Course, Question, Choice, Submission):
            self.assertIn(model, admin.site._registry)
        self.assertIn(Question, [inline.model for inline in admin.site._registry[Course].inlines])
        self.assertIn(Choice, [inline.model for inline in admin.site._registry[Question].inlines])
        staff = get_user_model().objects.create_superuser('course-admin', 'admin@example.test', 'Admin-tests-123!')
        instructor = Instructor.objects.create(user=staff, total_learners=0)
        self.client.force_login(staff)
        # A real image upload exercises the required Course.image admin field.
        gif = (b'GIF87a\x01\x00\x01\x00\x80\x00\x00\x00\x00\x00\xff\xff\xff'
               b',\x00\x00\x00\x00\x01\x00\x01\x00\x00\x02\x02D\x01\x00;')
        with tempfile.TemporaryDirectory() as media_root, override_settings(MEDIA_ROOT=media_root):
            response = self.client.post(reverse('admin:onlinecourse_course_add'), {
                'name': 'Admin-created course', 'description': 'Authored through the admin site',
                'image': SimpleUploadedFile('course.gif', gif, content_type='image/gif'),
                'pub_date': '2026-09-13', 'instructors': [instructor.pk], 'total_enrollment': 0,
                'lesson_set-TOTAL_FORMS': 1, 'lesson_set-INITIAL_FORMS': 0,
                'lesson_set-MIN_NUM_FORMS': 0, 'lesson_set-MAX_NUM_FORMS': 1000,
                'lesson_set-0-title': 'Admin lesson', 'lesson_set-0-order': 1,
                'lesson_set-0-content': 'Created as an inline lesson.',
                'question_set-TOTAL_FORMS': 1, 'question_set-INITIAL_FORMS': 0,
                'question_set-MIN_NUM_FORMS': 0, 'question_set-MAX_NUM_FORMS': 1000,
                'question_set-0-content': 'Which choice is correct?', 'question_set-0-grade': 50,
                '_save': 'Save',
            })
            self.assertEqual(response.status_code, 302, response.content.decode()[-6000:])
            course = Course.objects.get(name='Admin-created course')
            self.assertEqual(course.lesson_set.get().title, 'Admin lesson')
            question = course.question_set.get()
            response = self.client.post(reverse('admin:onlinecourse_question_change', args=[question.pk]), {
                'course': course.pk, 'content': question.content, 'grade': 50,
                'choice_set-TOTAL_FORMS': 2, 'choice_set-INITIAL_FORMS': 0,
                'choice_set-MIN_NUM_FORMS': 0, 'choice_set-MAX_NUM_FORMS': 1000,
                'choice_set-0-content': 'Correct answer', 'choice_set-0-is_correct': 'on',
                'choice_set-1-content': 'Incorrect answer', '_save': 'Save',
            })
            self.assertEqual(response.status_code, 302, response.content.decode()[-6000:])
            self.assertEqual(question.choice_set.count(), 2)
            self.assertEqual(question.choice_set.filter(is_correct=True).count(), 1)
            Enrollment.objects.create(user=staff, course=course)
            details = self.client.get(reverse('onlinecourse:course_details', args=[course.pk]))
            self.assertIs(details.context['exam_ready'], True)
            self.assertContains(details, 'Correct answer')
