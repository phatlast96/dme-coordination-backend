# Writeup

## Sequencing

_What did you build and how did you decide what to build first?_

---

To understand what to build first, I first wrote a research synthesis document to understand the problem and the solution. This is in the [synthesis.md](synthesis.md) file.

I then mapped the graph between the 3 parties (doctor, supplier, and Medicare) to understand the dependencies and flow of the process in [dme-coord-graph.jpg](dme-coord-graph.jpg) file.

After understanding the dependencies and the care advocate workflow, I started to map the conditions to triggers, success/failure modes, and actions to take.

The coordination requires a lot of follow-ups via phone calls so I added a table for follow-ups so that the patient can be able to follow along on actions taken on timeline. The followup table allows for idempotency and tracking of the actions taken. This keeps the patient in the loop. The patient, after all, needs to audit and be aware of the actions taken on their behalf.

I use AI/LLM and Twilio for voice to take phone calls and LLM to verify matching and verifying insurance requirements.

Added playwright to scrape the HTML for the requirements from a website for Medicare. Mocked OpenAI calls, Twilio calls, and other external systems. Added seed data for patient intake information and supplier contact information.

I noticed that Patient Advocates start with supplier list first instead of PCP. I started with PCP first in the flow starting with the patient intake form, because I assumed the inventory data is already available in the database, which is updated every time the AI talks to the supplier. Repeated follow-ups with the same supplier list before getting the order from PCP would annoy the supplier. Getting the order is a requirement for getting insurance claims for payments.


## Technology & Architecture

_What technologies, stack, and frameworks did you choose? Why? How is your pipeline wired?_

---

I used FastAPI for the API, SQLite as a mock database, Playwrite for scraping the requirements for Medicare, OpenAI for the LLM, and Twilio for the voice calls.

The pipeline is wired by starting with an patient intake form. That triggers the system to do follow-ups via phone calls on the PCP/doctor for the order. Once the order is confirmed, the system will trigger the follow-ups for the supplier to hand-off the order. The system will also try to verify that the supplier is enrolled in Medicare. If delivery is confirmed, the system will trigger follow-ups for insurance claims for payments.

- PCP chase until order + code match
- then supplier outreach → confirm delivery (silent → next supplier)
- then Medicare claim
- patient ping is side work after order; does not block the main path

1. POST /demo/start loads the patient intake form
2. AsyncIOScheduler loads due rows from scheduled_followups
3. For each due row, mocked Twilio dial and mocked OpenAI voice call to the designated person -> writes call_logs with success/failure
4. 'apply_call_outcome' function turns a finished phone call into the next step
    4a. 'schedule_followup' function (happens inside 'apply_call_outcome') schedules the next follow-up based on the outcome of the phone call


## The Cut List

_What did you deliberately decide not to include? Why?_

---
I decided to not include the sourcing of contact information regarding the PCP/doctor, supplier nor the Medicare. This is because I assumed the database is seeded with this information already.

I didn't include the UI as I want the focus to be on fixing the coordination problem.

Integration with external system is in the cutlist due to time constraints.

The documentation submission of the PCP order, supplier billing, and supplier enrollment to the insurance company as that require building a different system for interacting with the insurance portal. It is out of scope for this project.

Sending PCP order or any document submission including receipts and many other documents to any party for confirmation is also out of scope for this project.

Calculating the deductible and patient share is also out of scope for this project as it is assumed the insurance company will calculate this and the patient will pay their share.

## What's Next

_If you had 1 more day, what would you build? With 2 more weeks? Why did you choose that order?_

---
If I had 1 more day, I would build the following:
I would build a more robust transparent system so it's easy to audit for the patient and allows the patient to stay in the loop.

If I had 2 more weeks, I would focus on the voice calls as it is the main interface with all the parties involved. I want to be as natural as possible so that the person on the other end of the phone call don't feel like their time is spent talking to a robot.


I chose this order because observability is very important for coordination problems. It's hard to know what went wrong in the coordination process without a clear audit trail. After the observability is built, the focus on the voice calls to make the system seemless is the next logical step.


### Constraints Noted
-  Ideally around 3 hours. Time-boxing is suggested, but not a hard requirement. The 
scope is intentionally broad, so please prioritize what you think is most important. 
-  Skip auth, persistent DB, UI polish. Mock external systems freely. Be explicit about 
what's mocked. 
-  Any stack, any model, any framework. Use what you'd actually reach for in production. 
-  Use AI freely while building. We're not grading whether you wrote code by hand. What 
we care about is how you use AI inside the product. 