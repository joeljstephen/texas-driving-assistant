# Rule Summary

This project implements a simplified MVP policy subset for educational use.

## Out-of-State Transfer

- A new Texas resident with a valid, unexpired out-of-state license is classified as an out-of-state transfer.
- The flow is routed to an in-person application path.
- Knowledge and skills exams are generally not expected in this valid, unexpired transfer path.
- Texas residency still must be proven with two documents.
- The 30-day residency duration rule is represented as waived.
- The out-of-state license is listed as typically surrendered.
- The model emits guidance that new residents may generally drive with a valid out-of-state license for up to 90 days after moving to Texas.

## First-Time Adult Application

- A first-time adult applicant is routed to an in-person path.
- Required document categories include identity, lawful presence category if applicable, Social Security, and Texas residency.
- Age is requested because ages 18 through 24 require adult driver education.
- The rule base lists knowledge, skills, and vision testing for first-time applicants.
- If a skills test is needed, Impact Texas Drivers is included as a test-related requirement.

## Renewal

- Renewal is classified when the user indicates they are renewing a Texas license.
- The renewal window is modeled as up to two years before or after expiration.
- Online renewal is only inferred when the supporting eligibility facts are present: renewal timing is within the window, last renewal was in person, the applicant is under 79, health conditions are unchanged, license status is valid, there are no outstanding tickets or warrants, the applicant is a U.S. citizen, and SSN is on record.
- If online renewal support facts are missing or negative, the assistant conservatively routes toward a likely in-person path.
- If the timing appears outside the two-year window, the assistant routes to an original-application-style path rather than ordinary renewal.

## Replacement

- Lost, stolen, damaged, or replacement language classifies as replacement.
- If no front-of-card information changed, online replacement is only inferred when card number, date of birth, last-four SSN, and audit number are available.
- If those online replacement facts are missing, the assistant asks for them in order and treats the path as likely in-person until eligibility is supported.
- Address changes are handled through the replacement/change-info flow and may be online, mail, or in person when eligible.
- Stolen-card fraud produces guidance to file a police report.

## Next Question Priority

The s(CASP) program asks one highest-priority question at a time:

1. Goal or scenario
2. Out-of-state license presence
3. Out-of-state license validity and expiration
4. Age
5. Renewal timing
6. Renewal online-eligibility facts
7. Replacement front-of-card changes
8. Replacement online data fields
9. Document-related clarifiers
