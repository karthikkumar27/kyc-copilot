# SOP-KYC-01: Handling e-KYC rejections (LimauPay, fictional)

## Purpose
This SOP tells support agents how to explain an e-KYC rejection to a customer and how to help
them retry. It applies to MyKad, MyTentera and passport verification in the LimauPay app.

## Attempt limits
A customer gets 3 verification attempts in any rolling 24-hour period. After the third failed
attempt the app locks verification for 24 hours. Agents cannot reset the counter. A supervisor
may grant one extra attempt per customer per month using the Attempt Override action, which
requires a reason and is logged.

## Reason code DOC_BLURRY
The ID photo was not sharp enough to read. Ask the customer to place the card on a dark, flat
surface, hold the phone parallel to the card and wait for the frame to turn green before
capturing. Remove any card holder or sleeve.

## Reason code DOC_GLARE
Light reflected on the card covered part of the text or photo. Ask the customer to move away from
direct overhead lights or sunlight and tilt the card slightly.

## Reason code DOC_EXPIRED
The document has passed its expiry date. Passports must be valid for at least 6 months from the
date of verification. The customer must verify with a valid document; agents must not accept an
expired document on any grounds.

## Reason code NAME_MISMATCH
The name in the profile does not match the ID. The customer should edit their profile name to
match the ID exactly, including bin/binti, a/l or a/p, and then retry. Name changes after
successful verification require a new verification.

## Reason code SELFIE_MISMATCH
The selfie did not match the ID photo. Common causes are spectacles, face coverings, hats or poor
lighting. Ask the customer to remove them and retry in even light. If the ID photo is very old,
the customer may verify with a passport instead.

## Reason code LIVENESS_FAILED
The liveness video could not confirm a live person. Ask the customer to follow the on-screen
prompts slowly, keep their face inside the oval and use a stable internet connection.

## Reason code UNSUPPORTED_DOC
Accepted documents are MyKad, MyTentera and a valid international passport. Driving licences,
student cards and photocopies are not accepted.

## What agents must never do
Never ask the customer to send ID images through chat, email or social media. Never type a full
IC number into the ticket. Direct the customer to retry inside the app only.
