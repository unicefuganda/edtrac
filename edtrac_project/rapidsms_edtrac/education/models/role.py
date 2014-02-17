from django.contrib.auth.models import Group


class Role(Group):
    class Meta:
        app_label = 'education'
        proxy = True
        permissions = (
            (
                "can_report",
                "can  send data and receive data via text messages"
            ),
            (
                "can_view_one_school",
                "Access to View his/her school specific info"
            ),
            (
                "can_view_all_schools",
                "Access to View information from all schools"
            ),
            (
                "can_message_all",
                "Can send out mass text,polls etc"
            ),
            (
                "can_message_one_district",
                "Can send mass text,polls etc to district schools"
            ),
            (
                "can_view_one_district_verified",
                "Access to view verified district data"
            ),
            (
                "can_view_one_district_unverified",
                "Access to view district unverified  data"
            ),
            (
                "can_edit_one_district",
                "Access to edit his/her district specific info"
            ),
            (
                "can_verify_one_district",
                "Access to edit his/her district specific info"
            ),
            (
                "can_export_one_district",
                "Access to export his/her district specific info"
            ),
            (
                "can_export_all",
                "Access to export all data"
            ),
            (
                "can_schedule_special_script",
                "can send schedule special scripts"
            )
        )
