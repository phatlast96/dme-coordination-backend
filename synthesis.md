# Notes for Research Synthesis

## Overview of the Problem

Navigating DME (durable medical equipment) claims is a complex and time-consuming process.

3 parties involved:
- Patient
- Primary Care Doctor - writes the order
- DME Supplier - delivers the equipment and bills the insurance company

Every handoff is friction nad the patient is chasing all 3: insurance company, DME supplier and Primary Care Doctor.


## Overview of the Solution

Care advicates today on the team does this end-to-end.

Intake is handled — a patient has already called in and we have their situation documented

Hard part: coordinating across supplier, PCP, and Medicare, without a care advocate chasing each party by hand


## Zooming in on the Coordination Problem

coordinating across supplier, PCP, and Medicare, without a care advocate chasing each party by hand

Automate as much as possible.



### Background

Medicare (insurance company) will not pay unless
1. The Primary Care Doctor (PCP) writes an order
2. DME supplier is enrolled in Medicare

**Patient** gets stuck with full bill or never gets the equipment.

**DME Supplier** delivers the wheelchair and then bills Medicare directly; the patient typically owes a small share (~20%).

Nobody gets paid **until the order from PCP**, the supplier's enrollment, and the billing codes all line up. 


coordination problem: the doctor, the supplier, and Medicare each hold one piece, and the patient is left chasing all three.

US healthcare still runs heavily on phone and web portals — which is why "contacting the PCP" or "contacting a supplier" means a phone call, a web portal, or a callback, not a clean API. 



# What the care advocates do today

1.  Work the supplier list. Call enrolled suppliers from the directory. Ask each: taking new 
Medicare patients? Stock a standard manual wheelchair (K0001)? How soon could you 
deliver? Note who picks up, who doesn't, and call the no-answers back later. 
2.  Chase the written order. Contact the PCP's office for the formal order — call the front 
desk or work their portal, confirm it's moving, nudge again days later if it's still not signed. 
3.  Pin down the coverage. Confirm the patient's Medicare eligibility, check the coverage 
rules for the equipment, and find out whether it needs prior authorization before anyone 
can deliver. 
4.  Match and hand off. Once there's a real order and a supplier that's enrolled, in stock, 
and responsive, connect the two and get delivery scheduled — making sure the billing 
code on the claim matches what was ordered. 
5.  Keep the patient in the loop. Call along the way: what's happening, what she needs to 
do, what she'll owe (~20%), when to expect the equipment. 

# Look for

what the system does at each handoff, what triggers the next step, 
what happens when things go wrong