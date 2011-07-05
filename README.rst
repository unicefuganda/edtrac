Script
======
Rapidsms-script is a library that allows users to configure an automated series of questions, or schedule alerts/messages to go out after a fixed amount of time.

Models/Rules
------------
The main models used to create a script are Script and ScriptStep.  ScriptSteps are messages or polls (questions), along with a *transition rule* that explains how to proceed past this particular step in the script.  The rules are:
 - Lenient (for polls): accept erroneous responses and move on to the next step
 - Strict (for polls):wait until the user submits a valid response with no errors
 - Strict with retry then moveon : give the user n tries to send a valid response with no errors, resend the question n times if no response, then move on to the next step
 - Strict with retry then giveup : give the user n tries to send a valid response with no errors, resend the question n times if no response, then give up (exit the script)
 - Wait for <giveup_offset> seconds, then move to next step
 - Wait for <giveup_offset> seconds, then stop the script for this user entirely
 - Resend message/question <num_tries> times, then move to next step
 - Resend message/question <num_tries> times, then stop the script for this user entirely

Signals/Progress
----------------
The script application attempts to provide as much flexibility as possible by providing the above rules, however by design it avoids incorporating more complicated transition logic.  Rather, it emits three signals to allow other apps to change the normal, linear flow of a script.  Subscribers to any of these signals can change the associated ScriptProgress model, which maintains the state of a particular connection through a session of a script.
 - script_progress : sent just after a ScriptProgress goes to the next step
 - script_progress_pre_change : sent just after a ScriptProgress goes to the next step
 - script_progress_was_completed : sent just after ScriptProgress is completed

Autoregistration
----------------
One example use of a script is found in the Ureport auto registration process (https://github.com/daveycrockett/rapidsms-ureport/blob/master/ureport/management/commands/create_autoreg_script.py):
```
        script = Script.objects.create(
                slug="ureport_autoreg",
                name="uReport autoregistration script",
        )
        user = User.objects.get(username="admin")
        script.sites.add(Site.objects.get_current())
        script.steps.add(ScriptStep.objects.create(
            script=script,
            message="Welcome to Ureport, where you can SPEAK UP and BE HEARD on what is happening in your community-it's FREE! ",
            order=0,
            rule=ScriptStep.WAIT_MOVEON,
            start_offset=0,
            giveup_offset=60,
        ))
        poll = Poll.create_freeform("youthgroup", "First we need 2 know, are you part of a youth group? If yes, send us the NAME of the group. If no, text NO and just wait for the next set of instructions.", "", [], user)
        script.steps.add(ScriptStep.objects.create(
            script=script,
            poll=poll,
            order=1,
            rule=ScriptStep.RESEND_MOVEON,
            num_tries=1,
            start_offset=0,
            retry_offset=86400,
            giveup_offset=86400,
        ))
        script.steps.add(ScriptStep.objects.create(
            script=script,
            message="Ureport is a FREE SMS text message system that is sent to your phone.  Ureport is sponsored by UNICEF and other partners.",
            order=2,
            rule=ScriptStep.WAIT_MOVEON,
            start_offset=60,
            giveup_offset=60,
        ))
        poll4 = Poll.create_custom('district',"contactdistrict", "Its important to know which District you'll be reporting on so we can work together to try & resolve issues in your community!Reply ONLY with your district.", "", [], user)
        script.steps.add(ScriptStep.objects.create(
            script=script,
            poll=poll4,
            order=3,
            rule=ScriptStep.STRICT_MOVEON,
            start_offset=0,
            retry_offset=86400,
            num_tries=1,
            giveup_offset=86400,
        ))
        # and so on...
```
The Ureport app then subscribes to the `script_progress_was_completed` signal to pull responses from a script into the associated fields of a Contact model.

