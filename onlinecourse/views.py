"""Course browsing, enrolment, and authenticated exam submission/evaluation."""
from django.contrib.auth import authenticate, get_user_model, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.db.models import F
from django.http import HttpResponseBadRequest, HttpResponseForbidden
from django.shortcuts import get_object_or_404, redirect, render
from django.views import generic
from django.views.decorators.http import require_POST, require_http_methods

from .models import Course, Enrollment, Choice, Submission


@require_http_methods(['GET', 'POST'])
def registration_request(request):
    context = {}
    if request.method == 'POST':
        User = get_user_model()
        username = request.POST.get('username', '').strip()
        user = User(username=username, first_name=request.POST.get('firstname', '').strip(),
                    last_name=request.POST.get('lastname', '').strip())
        password = request.POST.get('psw', '')
        try:
            user.full_clean(exclude=['password'])
            validate_password(password, user)
            user.set_password(password)
            with transaction.atomic():
                user.save()
        except (ValidationError, IntegrityError) as error:
            context['message'] = ' '.join(error.messages) if isinstance(error, ValidationError) else 'User already exists.'
        else:
            login(request, user)
            return redirect('onlinecourse:index')
    return render(request, 'onlinecourse/user_registration_bootstrap.html', context)


@require_http_methods(['GET', 'POST'])
def login_request(request):
    context = {}
    if request.method == 'POST':
        user = authenticate(request, username=request.POST.get('username', ''), password=request.POST.get('psw', ''))
        if user is not None:
            login(request, user)
            return redirect('onlinecourse:index')
        context['message'] = 'Invalid username or password.'
    return render(request, 'onlinecourse/user_login_bootstrap.html', context)


@require_POST
def logout_request(request):
    logout(request)
    return redirect('onlinecourse:index')


def check_if_enrolled(user, course):
    return user.is_authenticated and Enrollment.objects.filter(user=user, course=course).exists()


def exam_is_ready(course):
    questions = list(course.question_set.all())
    return bool(questions) and all(any(c.is_correct for c in q.choice_set.all()) for q in questions)


class CourseListView(generic.ListView):
    template_name = 'onlinecourse/course_list_bootstrap.html'
    context_object_name = 'course_list'

    def get_queryset(self):
        courses = list(Course.objects.order_by('-total_enrollment', 'pk')[:10])
        enrolled = set(Enrollment.objects.filter(user=self.request.user).values_list('course_id', flat=True)) if self.request.user.is_authenticated else set()
        for course in courses:
            course.is_enrolled = course.pk in enrolled
        return courses


class CourseDetailView(generic.DetailView):
    model = Course
    template_name = 'onlinecourse/course_details_bootstrap.html'
    queryset = Course.objects.prefetch_related('lesson_set', 'question_set__choice_set')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['is_enrolled'] = check_if_enrolled(self.request.user, self.object)
        context['exam_ready'] = exam_is_ready(self.object)
        return context


@login_required
@require_POST
def enroll(request, course_id):
    course = get_object_or_404(Course, pk=course_id)
    with transaction.atomic():
        _, created = Enrollment.objects.get_or_create(user=request.user, course=course, defaults={'mode': Enrollment.HONOR})
        if created:
            Course.objects.filter(pk=course.pk).update(total_enrollment=F('total_enrollment') + 1)
    return redirect('onlinecourse:course_details', pk=course.pk)


def extract_answers(request):
    """Parse the supplied checkbox IDs; invalid IDs must never create a submission."""
    selected = set()
    for key, values in request.POST.lists():
        if key.startswith('choice'):
            if not key.startswith('choice_'):
                raise ValueError('Invalid choice field.')
            suffix = key.removeprefix('choice_')
            if not suffix.isdecimal() or int(suffix) <= 0 or len(values) != 1:
                raise ValueError('Invalid choice ID.')
            value = values[0]
            if not value.isdecimal() or int(value) != int(suffix):
                raise ValueError('Invalid choice ID.')
            selected.add(int(value))
    return selected


@login_required
@require_POST
def submit(request, course_id):
    """Save one exam attempt for the current learner's course enrollment."""
    course = get_object_or_404(Course.objects.prefetch_related('question_set__choice_set'), pk=course_id)
    enrollment = Enrollment.objects.filter(user=request.user, course=course).first()
    if enrollment is None:
        return HttpResponseForbidden('Enroll in this course before submitting an exam.')
    if not exam_is_ready(course):
        return HttpResponseBadRequest('This exam is not ready yet.')
    try:
        selected_ids = extract_answers(request)
    except (TypeError, ValueError):
        return HttpResponseBadRequest('Invalid exam choices.')
    choices = list(Choice.objects.filter(pk__in=selected_ids, question__course=course))
    if {choice.pk for choice in choices} != selected_ids:
        return HttpResponseBadRequest('Every selected choice must belong to this course.')
    with transaction.atomic():
        submission = Submission.objects.create(enrollment=enrollment)
        submission.choices.set(choices)
    return redirect('onlinecourse:exam_result', course_id=course.pk, submission_id=submission.pk)


@login_required
def show_exam_result(request, course_id, submission_id):
    """Evaluate a learner-owned attempt, awarding points for exact answer sets."""
    course = get_object_or_404(Course.objects.prefetch_related('question_set__choice_set'), pk=course_id)
    submission = get_object_or_404(Submission.objects.select_related('enrollment').prefetch_related('choices'),
                                   pk=submission_id, enrollment__course=course, enrollment__user=request.user)
    selected_ids = {choice.pk for choice in submission.choices.all()}
    total_score = 0
    max_score = 0
    question_results = []
    for question in course.question_set.all():
        choices = list(question.choice_set.all())
        correct_ids = {choice.pk for choice in choices if choice.is_correct}
        chosen_ids = {choice.pk for choice in choices if choice.pk in selected_ids}
        is_correct = bool(correct_ids) and chosen_ids == correct_ids
        earned = question.grade if is_correct else 0
        total_score += earned
        max_score += question.grade
        question_results.append({'question': question, 'is_correct': is_correct, 'earned': earned,
                                 'choices': [{'choice': choice, 'selected': choice.pk in selected_ids} for choice in choices]})
    grade = 100 * total_score / max_score if max_score else 0
    context = {'course': course, 'submission': submission, 'choices': submission.choices.all(),
               'grade': grade, 'total_score': total_score, 'max_score': max_score,
               'passed': max_score > 0 and total_score * 100 > max_score * 80,
               'question_results': question_results}
    return render(request, 'onlinecourse/exam_result_bootstrap.html', context)
