<!-- synthetic fixture: invented text for tests, not Anant's writing -->
Subject: Platform intern role and the build queue

Hi Priya,

I am a second-year computer science student and I applied to the platform engineering intern role last week. I read your talk on moving nightly tests to spot machines and wanted to reach out directly, because I spent last summer on a smaller version of the same problem at my campus robotics lab.

Our nightly build ran on one shared server and took about three hours. I split it into jobs, wrote a small queue in Python that handed them to four idle lab machines, and added a retry for jobs that died when a student logged in. The build dropped to forty minutes. My first version retried everything, which hid a compiler bug for a week, so I changed it to retry only on a lost machine.

This spring I also wrote a log grouper in Go that links each failure to the commit that started it, and two other student teams now use it for their own builds.

Would you have fifteen minutes in the next two weeks to tell me how your team decides what is safe to cache between runs?

Thanks,
Jordan
