from django.contrib import admin
from django.contrib.auth import get_user_model
from django.db.models import ForeignKey
from django.db.models.expressions import RawSQL
from import_export import resources, widgets, fields
from import_export.admin import ImportMixin

from sport.models import Student, MedicalGroup
from sport.signals import get_or_create_student_group
from .inlines import ViewAttendanceInline, AddAttendanceInline
from .site import site
from .utils import user__email, has_enrolled_filter


class MedicalGroupWidget(widgets.ForeignKeyWidget):
    def render(self, value: MedicalGroup, obj=None):
        return str(value)


class StudentResource(resources.ModelResource):
    medical_group = fields.Field(
        column_name="medical_group",
        attribute="medical_group",
        widget=MedicalGroupWidget(MedicalGroup, "pk"),
    )

    def get_or_init_instance(self, instance_loader, row):
        student_group = get_or_create_student_group()
        user_model = get_user_model()
        user, _ = user_model.objects.get_or_create(
            email=row["email"],
            defaults={
                "first_name": row["first_name"],
                "last_name": row["last_name"],
                "username": row["email"],
            },
        )

        student_model_fields = [
            f.name
            for f in Student._meta.fields
            if not isinstance(f, ForeignKey)
        ]

        student_import_fields = row.keys() & student_model_fields

        student, student_created = Student.objects.get_or_create(
            user=user,
            defaults=dict([
                (key, row[key])
                for key in student_import_fields
            ])
        )
        if student_created:
            user.groups.add(student_group)

        return student, student_created

    class Meta:
        model = Student
        fields = (
            "user",
            "user__email",
            "user__first_name",
            "user__last_name",
            "enrollment_year",
        )
        export_order = (
            "user",
            "user__email",
            "user__first_name",
            "user__last_name",
            "medical_group",
            "enrollment_year",
        )
        import_id_fields = ("user",)


@admin.register(Student, site=site)
class StudentAdmin(ImportMixin, admin.ModelAdmin):
    resource_class = StudentResource

    autocomplete_fields = (
        "user",
    )

    search_fields = (
        "user__first_name",
        "user__last_name",
        "user__email",
    )

    list_filter = (
        "is_ill",
        "enrollment_year",
        "medical_group",
        has_enrolled_filter(),
    )

    list_display = (
        "__str__",
        user__email,
        "is_ill",
        "medical_group",
        "has_enrolled",
    )

    readonly_fields = (
        "has_enrolled",
    )

    def has_enrolled(self, obj):
        return obj.has_enrolled

    has_enrolled.boolean = True

    ordering = (
        "user__first_name",
        "user__last_name"
    )

    inlines = (
        ViewAttendanceInline,
        AddAttendanceInline,
    )

    list_select_related = (
        "user",
        "medical_group",
    )

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.annotate(has_enrolled=RawSQL(
            'SELECT count(*) > 0 FROM enroll, "group" '
            'WHERE student_id = student.user_id '
            'AND "group".semester_id = current_semester() '
            'AND "group".id = enroll.group_id '
            'AND enroll.is_primary = True',
            ()
        ))
