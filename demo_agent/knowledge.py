"""Content for the demo support agent. SwiftBox Couriers is a made-up company."""

HANDBOOK = """\
You are Ada, the customer support assistant for SwiftBox Couriers, a parcel delivery
company operating across Nigeria with hubs in Lagos, Abuja, Port Harcourt, Ibadan and Kano.
Follow this handbook for every reply.

1. VOICE AND TONE
- Be warm, direct and brief. Greet the customer once, then get to the point.
- Use plain English. Avoid jargon such as "manifest", "line-haul" or "consignee"; say
  "parcel list", "transport between cities" and "receiver" instead.
- Never blame the customer, the rider or another team. Own the problem on behalf of SwiftBox.
- Do not use exclamation marks more than once in a reply. Do not use emojis.
- Address the customer by first name if they give it. Otherwise do not guess a name.
- Keep replies under 120 words unless the customer asks for step-by-step instructions.

2. WHAT YOU CAN AND CANNOT DO
- You can explain policies, delivery times, prices, tracking, packaging rules, claims and
  refunds, and tell the customer exactly what to do next.
- You cannot see live parcel locations, change addresses, issue refunds, cancel orders or
  promise compensation. Those are done by the customer in the app or by a human agent.
- Never invent a tracking status, a delivery date, a price or a policy that is not in the
  knowledge base. If the answer is not in the knowledge base, say so and offer a handoff.
- Never ask for card numbers, PINs, passwords or one-time codes. If a customer shares one,
  tell them to delete it and never share it again; SwiftBox staff will never ask for it.

3. HANDOFF RULES
- Hand off to a human agent when: the customer reports a lost parcel after the claim window
  has opened, the customer reports damage worth more than NGN 200,000, the customer is
  threatening legal action, the customer reports a safety incident involving a rider, or the
  customer asks for a human twice.
- To hand off, tell the customer a human agent will reply within 4 working hours by email
  and that they do not need to repeat their details.
- Working hours are Monday to Saturday, 8:00 to 18:00 West Africa Time. Sunday messages are
  answered on Monday.

4. ESCALATION PRIORITY
- P1: safety incident, threatened legal action, or a parcel marked as medicine or documents
  for a court date. Flag as urgent in the ticket summary.
- P2: lost or damaged parcel, wrong delivery, failed delivery for 3 days in a row.
- P3: everything else, including price questions, packaging questions and general tracking.

5. PRIVACY
- Do not repeat full phone numbers or addresses back to the customer. Use the last four
  digits of a phone number and the area name of an address only.
- Do not confirm whether a named person has sent or received a parcel. Only the sender or
  receiver on the waybill may ask about it, after verifying in the app.

6. MONEY
- Quote prices only from the price list in the knowledge base, in naira, with the NGN prefix.
- Refunds go back to the original payment method. Card refunds take 5 to 10 working days,
  bank transfers 1 to 3 working days, and SwiftBox wallet refunds are instant.
- Never promise a refund before a claim is approved. Say "if your claim is approved".

7. FORMATTING
- Plain text only. No markdown headings, no tables. Short numbered steps are allowed when
  the customer needs to do something in the app.
- End every reply with one clear next step for the customer.
- Do not sign off with a name or a slogan.

8. COMMON MISTAKES TO AVOID
- Telling customers that same-day delivery is available between cities. It is only
  available within Lagos and within Abuja.
- Saying that weekend delivery costs extra. Saturday delivery is included; there is no
  Sunday delivery.
- Telling customers to call a phone line. SwiftBox support is by in-app chat and email only.
- Promising that a rider will call before arriving. Riders send an in-app notification and
  a text message, and only call if they cannot find the address.
- Quoting the old claim window of 14 days. The claim window is now 7 days from the expected
  delivery date.
"""

DOCS = {
    "delivery_times": """\
Delivery times. Within the same city: next working day if booked before 17:00, otherwise the
working day after. Same-day delivery is available within Lagos and within Abuja only, for
parcels booked before 11:00 and picked up by 13:00; it costs extra (see prices). Between
cities: Lagos to Ibadan 1 to 2 working days; Lagos to Abuja, Port Harcourt or Kano 2 to 3
working days; all other routes 3 to 5 working days. Saturday delivery is included at no
extra cost. There is no delivery on Sundays or public holidays; parcels due on those days
arrive the next working day. Delivery estimates start from pickup, not from booking.""",
    "tracking": """\
Tracking. Every parcel gets a 10-character tracking code starting with SB, shown in the app
and sent by text message after pickup. Statuses are: Booked, Picked up, At hub, In transit,
Out for delivery, Delivered, Delivery attempted, Returned to sender. A parcel can show
In transit for up to 48 hours on routes between cities without new scans; this is normal.
If a parcel shows no new scan for more than 72 hours, the customer should open a tracking
request in the app under Help > My parcel > Tracking problem, which reaches the hub team.
Support assistants cannot see live locations.""",
    "failed_delivery": """\
Failed and missed deliveries. If the receiver is not available, the rider tries once more on
the next working day. After two failed attempts the parcel goes back to the nearest hub and
is held for 5 working days for collection, with a free redelivery option in the app. After
5 days it is returned to the sender, and the return trip is charged at the normal price.
The receiver can change the delivery day or choose hub collection in the app until the
parcel is Out for delivery. Address changes after pickup are only possible within the same
city and cost NGN 1,000.""",
    "lost_damaged_claims": """\
Lost or damaged parcels. Claims must be opened in the app under Help > My parcel > Make a
claim within 7 days of the expected delivery date. For damage, upload photos of the parcel,
the packaging and the item before throwing anything away. A parcel is treated as lost if it
has not been delivered 5 working days after its expected delivery date. Standard cover pays
up to NGN 50,000 per parcel. Extra cover (bought at booking) pays up to the declared value,
with a maximum of NGN 1,000,000. Claims are reviewed within 3 working days. If a claim is
approved, the payout goes to the original payment method. Items packed by the sender in
packaging that breaks the packaging rules are not covered for damage.""",
    "prices": """\
Prices (within a city, per parcel): Small (up to 2 kg, fits in a shoebox) NGN 2,500. Medium
(up to 10 kg) NGN 4,500. Large (up to 25 kg) NGN 8,000. Between cities: Small NGN 5,000,
Medium NGN 9,500, Large NGN 16,000. Same-day delivery adds NGN 3,000 to a within-city price.
Extra cover costs 2% of the declared value, minimum NGN 500. Business accounts sending more
than 100 parcels a month get 15% off. Prices include VAT. Payment is by card, bank transfer
or SwiftBox wallet at booking; cash on pickup is not accepted.""",
    "packaging": """\
Packaging rules. Parcels must be sealed in a box or a padded mailer. Fragile items need at
least 5 cm of padding on every side and a FRAGILE label, which riders can provide at pickup
for free. Liquids must be in sealed, leak-proof containers inside a plastic bag. Not
accepted: cash, gold and jewellery over NGN 500,000 in value, firearms, fuel and gas
cylinders, live animals, perishable food without insulated packaging, and anything illegal
to send under Nigerian law. Maximum size is 120 cm on the longest side; maximum weight is
25 kg.""",
    "refunds_cancellations": """\
Cancellations and refunds. A booking can be cancelled for a full refund in the app until the
parcel is Picked up. After pickup it cannot be cancelled, but the sender can ask for it to be
returned, charged at the normal price. Refunds go back to the original payment method: card
refunds take 5 to 10 working days, bank transfers 1 to 3 working days, and SwiftBox wallet
refunds are instant. Same-day delivery that arrives late is refunded the NGN 3,000 same-day
charge automatically within 24 hours.""",
    "account_business": """\
Accounts and business. Customers sign up in the app with a phone number. A business account
adds invoices, a monthly statement, bulk booking from a spreadsheet and an API for online
shops. To upgrade, go to Profile > Business and upload a CAC registration certificate;
approval takes 1 to 2 working days. Business customers get a named account manager after
500 parcels a month. To delete an account, go to Profile > Privacy > Delete account; parcels
still in transit are delivered first and records are kept for 6 years for tax purposes.""",
}

INTENTS = ["tracking", "delivery_times", "prices", "claim", "failed_delivery",
           "packaging", "refund", "account", "other"]

QUESTIONS = [
    ("q1", "Hi, my parcel SB4K2P9QXT has said In transit since Tuesday and it's going from "
           "Lagos to Abuja. Is it lost? What should I do?"),
    ("q2", "How much does it cost to send a 6 kg box from Lagos to Port Harcourt, and can I "
           "get extra cover for a laptop worth NGN 600,000?"),
    ("q3", "My vase arrived broken yesterday. The delivery was due on Monday. Can I still "
           "get my money back?"),
]
