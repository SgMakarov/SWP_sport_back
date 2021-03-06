from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import render, redirect
from django.utils import timezone
from django import forms
from rest_framework.decorators import api_view, permission_classes

from api.crud import get_ongoing_semester, get_student_groups, get_brief_hours, get_trainer_groups
from api.permissions import IsStudent
from sport.models import Student, MedicalGroupReference
from sport.utils import set_session_notification


class MedicalGroupReferenceForm(forms.Form):
    reference = forms.ImageField()


def parse_group(group: dict) -> dict:
    return {
        "id": group["id"],
        "is_primary": group.get("is_primary", None),
        'qualified_name': f'{group["name"]} ({group["sport_name"]})',
        "name": group["name"],
        "sport": group["sport_name"]
    }


@login_required
def profile_view(request, **kwargs):
    user = request.user

    student = Student.objects.filter(pk=user.pk).select_related("medical_group").first()  # type: Optional[Student]
    trainer = getattr(user, "trainer", None)  # type: Optional[Trainer]

    current_semester = get_ongoing_semester()
    utc_date = timezone.localdate(timezone=timezone.utc)

    context = {
        "user": request.user,
        "common": {
            "semester_name": current_semester.name
        },
        "forms": {
            "medical_group_reference": MedicalGroupReferenceForm()
        },
    }

    if "notify" in request.session:
        msg_type, msg = request.session["notify"]
        context.update({
            "notify": {
                "msg": msg,
                "type": msg_type,
            }
        })
        del request.session["notify"]

    if student is not None:
        student_groups = get_student_groups(student)
        student_groups_parsed = list(map(
            parse_group,
            student_groups
        ))
        student_brief_hours_info = get_brief_hours(student)
        student_data = student.__dict__
        has_med_group_submission = MedicalGroupReference.objects.filter(
            student=student,
            semester=current_semester,
        ).exists()

        secondary_groups = len([
            group
            for group in student_groups_parsed
            if not group["is_primary"]
        ])
        context.update({
            "student": {
                "student_id": student.pk,
                "sport_groups": student_groups_parsed,
                "no_primary_group": secondary_groups == len(student_groups_parsed),
                "secondary_group_left": 2 - secondary_groups,
                "semesters": student_brief_hours_info,
                "obj": student,
                "has_med_group_submission": has_med_group_submission,
                **student_data,
            },
        })

    if trainer is not None:
        training_groups = list(map(
            parse_group,
            get_trainer_groups(trainer)
        ))
        trainer_data = trainer.__dict__
        context.update({
            "trainer": {
                "sport_groups": training_groups,
                "obj": trainer,
                **trainer_data,
            },
        })

    return render(request, "profile.html", context)


@api_view(["POST"])
@permission_classes([IsStudent])
def process_med_group_form(request, *args, **kwargs):
    form = MedicalGroupReferenceForm(request.POST, request.FILES)
    if form.is_valid():
        obj, created = MedicalGroupReference.objects.get_or_create(
            student_id=request.user.pk,
            defaults={
                "image": form.cleaned_data["reference"],
                "semester": get_ongoing_semester(),
            },
        )

        if created:
            set_session_notification(
                request,
                "Successful submit",
                "success",
            )
            return redirect('profile')
        else:
            set_session_notification(
                request,
                "You have already submitted reference",
                "error",
            )
    else:
        set_session_notification(request, "Form is invalid", "error")
    return redirect('profile')
