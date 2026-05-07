% Main s(CASP) knowledge base for adult, non-commercial Texas driver-license guidance.

% --------------------------------------------------
% Optional input predicates
% --------------------------------------------------

goal(__none) :- false.
age(-1) :- false.
renewal_timing(__none) :- false.
adult_driver_education_status(__none) :- false.

applying_texas_license :- false.
new_texas_resident :- false.

has_out_of_state_license :- false.
-has_out_of_state_license :- false.
no_out_of_state_license :- false.

out_of_state_license_valid :- false.
-out_of_state_license_valid :- false.
out_of_state_license_invalid :- false.

out_of_state_license_unexpired :- false.
-out_of_state_license_unexpired :- false.
out_of_state_license_expired :- false.
out_of_state_license_expired_not_over_two_years :- false.
out_of_state_license_expired_over_two_years :- false.

has_texas_license :- false.
-has_texas_license :- false.
no_texas_license :- false.

front_card_changed :- false.
-front_card_changed :- false.
no_front_card_changed :- false.
name_change_requested :- false.
address_change_requested :- false.

license_lost_stolen_damaged :- false.
license_stolen_and_fraud_used :- false.

has_identity_doc :- false.
has_social_security :- false.
has_texas_residency_docs :- false.
lawful_presence_category_known :- false.
lawful_presence_on_record :- false.

owns_vehicle :- false.
-owns_vehicle :- false.
no_vehicle_owned :- false.
has_proof_of_insurance :- false.
has_texas_vehicle_registration :- false.

has_card_number :- false.
has_date_of_birth_for_online :- false.
has_last4_ssn :- false.
has_audit_number :- false.

us_citizen :- false.
-us_citizen :- false.
not_us_citizen :- false.
ssn_on_record :- false.
-ssn_on_record :- false.
ssn_not_on_record :- false.

last_renewed_in_person :- false.
-last_renewed_in_person :- false.
last_renewed_not_in_person :- false.
license_valid_status :- false.
-license_valid_status :- false.
license_invalid_status :- false.
no_outstanding_tickets_or_warrants :- false.
-no_outstanding_tickets_or_warrants :- false.
outstanding_tickets_or_warrants :- false.
health_conditions_unchanged :- false.
-health_conditions_unchanged :- false.
health_conditions_changed :- false.

-adult_scope :- false.
-inferred_case(__none) :- false.
-service_mode(__none) :- false.

% --------------------------------------------------
% Strict normalization and classical negation
% --------------------------------------------------

goal_is(first_time) :- goal(first_time).
goal_is(first_time) :- goal(first_time_application).
goal_is(first_time) :- goal(apply).
goal_is(first_time) :- goal(new_license).

goal_is(transfer) :- goal(transfer).
goal_is(transfer) :- goal(out_of_state_transfer).
goal_is(transfer) :- goal(transfer_out_of_state).

goal_is(renewal) :- goal(renewal).
goal_is(renewal) :- goal(renew).
goal_is(renewal) :- goal(renew_license).

goal_is(replacement) :- goal(replacement).
goal_is(replacement) :- goal(replace).
goal_is(replacement) :- goal(replace_lost_license).

goal_is(change_info) :- goal(change_info).
goal_is(change_info) :- goal(change_address).
goal_is(change_info) :- goal(change_name).

knows_goal :- goal_is(first_time).
knows_goal :- goal_is(transfer).
knows_goal :- goal_is(renewal).
knows_goal :- goal_is(replacement).
knows_goal :- goal_is(change_info).

-has_out_of_state_license :- no_out_of_state_license.
-out_of_state_license_valid :- out_of_state_license_invalid.
-out_of_state_license_unexpired :- out_of_state_license_expired.
-has_texas_license :- no_texas_license.
-front_card_changed :- no_front_card_changed.
-owns_vehicle :- no_vehicle_owned.
-us_citizen :- not_us_citizen.
-ssn_on_record :- ssn_not_on_record.
-last_renewed_in_person :- last_renewed_not_in_person.
-license_valid_status :- license_invalid_status.
-no_outstanding_tickets_or_warrants :- outstanding_tickets_or_warrants.
-health_conditions_unchanged :- health_conditions_changed.

out_of_state_license_expired :- out_of_state_license_expired_not_over_two_years.
out_of_state_license_expired :- out_of_state_license_expired_over_two_years.
out_of_state_license_expired :- -out_of_state_license_unexpired.
-out_of_state_license_expired_over_two_years :- out_of_state_license_expired_not_over_two_years.
-out_of_state_license_expired_not_over_two_years :- out_of_state_license_expired_over_two_years.

front_of_card_info_changed :- front_card_changed.
front_of_card_info_changed :- name_change_requested.
front_of_card_info_changed :- address_change_requested.

age_known :- age(_).
under_18 :- age(A), A < 18.
age_18_to_24 :- age(A), A >= 18, A =< 24.
under_79 :- age(A), A < 79.

knows_out_of_state_license_presence :- has_out_of_state_license.
knows_out_of_state_license_presence :- -has_out_of_state_license.

knows_out_of_state_validity :- out_of_state_license_valid.
knows_out_of_state_validity :- -out_of_state_license_valid.

knows_out_of_state_expiration :- out_of_state_license_unexpired.
knows_out_of_state_expiration :- out_of_state_license_expired.
knows_out_of_state_expiration :- -out_of_state_license_unexpired.

knows_renewal_timing :- renewal_timing(_).

knows_front_card_change :- front_card_changed.
knows_front_card_change :- -front_card_changed.
knows_front_card_change :- name_change_requested.
knows_front_card_change :- address_change_requested.

knows_last_renewal_method :- last_renewed_in_person.
knows_last_renewal_method :- -last_renewed_in_person.

knows_license_status :- license_valid_status.
knows_license_status :- -license_valid_status.

knows_health_change :- health_conditions_unchanged.
knows_health_change :- -health_conditions_unchanged.

knows_citizenship_for_online_renewal :- us_citizen.
knows_citizenship_for_online_renewal :- -us_citizen.

knows_ssn_on_record :- ssn_on_record.
knows_ssn_on_record :- -ssn_on_record.

renewal_window_ok :- renewal_timing(within_window).
renewal_window_ok :- renewal_timing(within_two_years_before).
renewal_window_ok :- renewal_timing(expires_within_two_years).
renewal_window_ok :- renewal_timing(expired_less_than_two_years).

renewal_window_outside :- renewal_timing(outside_window).
renewal_window_outside :- renewal_timing(expired_more_than_two_years).

valid_unexpired_transfer_credential :-
    has_out_of_state_license,
    out_of_state_license_valid,
    out_of_state_license_unexpired.

recognized_transfer_waiver_credential :-
    valid_unexpired_transfer_credential.

recognized_transfer_waiver_credential :-
    has_out_of_state_license,
    out_of_state_license_expired_not_over_two_years.

online_replacement_ready :-
    has_card_number,
    has_date_of_birth_for_online,
    has_last4_ssn,
    has_audit_number.

% --------------------------------------------------
% Constraints
% --------------------------------------------------

false :- has_out_of_state_license, -has_out_of_state_license.
false :- out_of_state_license_valid, -out_of_state_license_valid.
false :- out_of_state_license_unexpired, -out_of_state_license_unexpired.
false :- out_of_state_license_unexpired, out_of_state_license_expired.
false :- out_of_state_license_expired_not_over_two_years, out_of_state_license_expired_over_two_years.
false :- has_texas_license, -has_texas_license.
false :- front_card_changed, -front_card_changed.
false :- owns_vehicle, -owns_vehicle.
false :- us_citizen, -us_citizen.
false :- ssn_on_record, -ssn_on_record.
false :- last_renewed_in_person, -last_renewed_in_person.
false :- license_valid_status, -license_valid_status.
false :- no_outstanding_tickets_or_warrants, -no_outstanding_tickets_or_warrants.
false :- health_conditions_unchanged, -health_conditions_unchanged.
false :- under_18, age_18_to_24.

% --------------------------------------------------
% Scenario signals
% --------------------------------------------------

case_candidate(replacement) :- goal_is(replacement).
case_candidate(replacement) :- goal_is(change_info).
case_candidate(replacement) :-
    not knows_goal,
    has_texas_license,
    license_lost_stolen_damaged.
case_candidate(replacement) :-
    not knows_goal,
    has_texas_license,
    name_change_requested.
case_candidate(replacement) :-
    not knows_goal,
    has_texas_license,
    address_change_requested.

case_candidate(renewal) :- goal_is(renewal).
case_candidate(renewal) :-
    not knows_goal,
    has_texas_license,
    knows_renewal_timing,
    not license_lost_stolen_damaged,
    not name_change_requested,
    not address_change_requested.

case_candidate(out_of_state_transfer) :- goal_is(transfer).
case_candidate(out_of_state_transfer) :-
    not knows_goal,
    new_texas_resident,
    has_out_of_state_license.

case_candidate(first_time_application) :- goal_is(first_time).
case_candidate(first_time_application) :-
    not knows_goal,
    applying_texas_license,
    -has_out_of_state_license,
    not case_candidate(renewal),
    not case_candidate(replacement).
case_candidate(first_time_application) :-
    not knows_goal,
    -has_texas_license,
    -has_out_of_state_license,
    applying_texas_license,
    not case_candidate(renewal),
    not case_candidate(replacement).

can_infer_scenario_without_goal :- case_candidate(replacement).
can_infer_scenario_without_goal :- case_candidate(renewal).
can_infer_scenario_without_goal :- case_candidate(out_of_state_transfer).
can_infer_scenario_without_goal :- case_candidate(first_time_application).

transfer_case :- case_candidate(out_of_state_transfer).
renewal_case :- case_candidate(renewal).
replacement_case :- case_candidate(replacement).
first_time_case :- case_candidate(first_time_application).

% --------------------------------------------------
% Defaults and strong exceptions for case classification
% --------------------------------------------------

adult_scope :-
    not ab(d_adult_scope),
    not -adult_scope.

ab(d_adult_scope) :- under_18.
-adult_scope :- under_18.

inferred_case(out_of_scope_under_18) :- under_18.

inferred_case(replacement) :-
    case_candidate(replacement),
    adult_scope,
    not ab(d_case_replacement),
    not -inferred_case(replacement).
ab(d_case_replacement) :- under_18.
-inferred_case(replacement) :- under_18.

inferred_case(renewal) :-
    case_candidate(renewal),
    adult_scope,
    not ab(d_case_renewal),
    not -inferred_case(renewal).
ab(d_case_renewal) :- under_18.
ab(d_case_renewal) :- case_candidate(replacement).
-inferred_case(renewal) :- under_18.
-inferred_case(renewal) :- case_candidate(replacement).

inferred_case(out_of_state_transfer) :-
    case_candidate(out_of_state_transfer),
    adult_scope,
    not ab(d_case_transfer),
    not -inferred_case(out_of_state_transfer).
ab(d_case_transfer) :- under_18.
ab(d_case_transfer) :- case_candidate(replacement).
ab(d_case_transfer) :- case_candidate(renewal).
-inferred_case(out_of_state_transfer) :- under_18.
-inferred_case(out_of_state_transfer) :- case_candidate(replacement).
-inferred_case(out_of_state_transfer) :- case_candidate(renewal).

inferred_case(first_time_application) :-
    case_candidate(first_time_application),
    adult_scope,
    not ab(d_case_first_time),
    not -inferred_case(first_time_application).
ab(d_case_first_time) :- under_18.
ab(d_case_first_time) :- case_candidate(replacement).
ab(d_case_first_time) :- case_candidate(renewal).
ab(d_case_first_time) :- case_candidate(out_of_state_transfer).
-inferred_case(first_time_application) :- under_18.
-inferred_case(first_time_application) :- case_candidate(replacement).
-inferred_case(first_time_application) :- case_candidate(renewal).
-inferred_case(first_time_application) :- case_candidate(out_of_state_transfer).

application_case :- inferred_case(first_time_application).
application_case :- inferred_case(out_of_state_transfer).

% --------------------------------------------------
% Missing information
% --------------------------------------------------

missing_info(goal) :-
    not knows_goal,
    not can_infer_scenario_without_goal.

missing_info(out_of_state_license_presence) :-
    goal_is(transfer),
    not knows_out_of_state_license_presence.

missing_info(out_of_state_license_validity) :-
    transfer_case,
    has_out_of_state_license,
    not knows_out_of_state_validity.

missing_info(out_of_state_license_expiration) :-
    transfer_case,
    has_out_of_state_license,
    not knows_out_of_state_expiration.

missing_info(out_of_state_two_year_expiration_detail) :-
    transfer_case,
    out_of_state_license_expired,
    not out_of_state_license_expired_not_over_two_years,
    not out_of_state_license_expired_over_two_years.

missing_info(age) :-
    first_time_case,
    not age_known.
missing_info(age) :-
    transfer_case,
    not age_known.
missing_info(age) :-
    renewal_case,
    not age_known.

missing_info(renewal_timing) :-
    renewal_case,
    not knows_renewal_timing.

missing_info(last_renewal_method) :-
    renewal_case,
    renewal_window_ok,
    not knows_last_renewal_method.

missing_info(health_change) :-
    renewal_case,
    renewal_window_ok,
    not knows_health_change.

missing_info(license_status) :-
    renewal_case,
    renewal_window_ok,
    not knows_license_status.

missing_info(outstanding_tickets_or_warrants) :-
    renewal_case,
    renewal_window_ok,
    license_valid_status,
    not no_outstanding_tickets_or_warrants,
    not outstanding_tickets_or_warrants.

missing_info(citizenship_for_online_renewal) :-
    renewal_case,
    renewal_window_ok,
    not knows_citizenship_for_online_renewal.

missing_info(ssn_on_record) :-
    renewal_case,
    renewal_window_ok,
    not knows_ssn_on_record.

missing_info(front_card_changed) :-
    replacement_case,
    not knows_front_card_change.

missing_info(card_number_for_online_replacement) :-
    inferred_case(replacement),
    -front_card_changed,
    not has_card_number.

missing_info(date_of_birth_for_online_replacement) :-
    inferred_case(replacement),
    -front_card_changed,
    has_card_number,
    not has_date_of_birth_for_online.

missing_info(last4_ssn_for_online_replacement) :-
    inferred_case(replacement),
    -front_card_changed,
    has_card_number,
    has_date_of_birth_for_online,
    not has_last4_ssn.

missing_info(audit_number_for_online_replacement) :-
    inferred_case(replacement),
    -front_card_changed,
    has_card_number,
    has_date_of_birth_for_online,
    has_last4_ssn,
    not has_audit_number.

missing_info(residency_documents) :-
    application_case,
    not has_texas_residency_docs.

missing_info(identity_documents) :-
    application_case,
    not has_identity_doc.

missing_info(social_security) :-
    application_case,
    not has_social_security.

missing_info(lawful_presence_category) :-
    application_case,
    not lawful_presence_category_known.

% --------------------------------------------------
% Highest-priority next question
% --------------------------------------------------

next_question(ask_goal) :- missing_info(goal).

next_question(ask_out_of_state_license_presence) :-
    not missing_info(goal),
    missing_info(out_of_state_license_presence).

next_question(ask_out_of_state_validity) :-
    not missing_info(goal),
    not missing_info(out_of_state_license_presence),
    missing_info(out_of_state_license_validity).

next_question(ask_out_of_state_expiration) :-
    not missing_info(goal),
    not missing_info(out_of_state_license_presence),
    not missing_info(out_of_state_license_validity),
    missing_info(out_of_state_license_expiration).

next_question(ask_if_out_of_state_expired_more_than_two_years) :-
    not missing_info(goal),
    not missing_info(out_of_state_license_presence),
    not missing_info(out_of_state_license_validity),
    not missing_info(out_of_state_license_expiration),
    missing_info(out_of_state_two_year_expiration_detail).

next_question(ask_age) :-
    not missing_info(goal),
    not missing_info(out_of_state_license_presence),
    not missing_info(out_of_state_license_validity),
    not missing_info(out_of_state_license_expiration),
    not missing_info(out_of_state_two_year_expiration_detail),
    missing_info(age).

next_question(ask_renewal_timing) :-
    not missing_info(goal),
    not missing_info(age),
    missing_info(renewal_timing).

next_question(ask_last_renewal_method) :-
    not missing_info(goal),
    not missing_info(age),
    not missing_info(renewal_timing),
    missing_info(last_renewal_method).

next_question(ask_health_change) :-
    not missing_info(goal),
    not missing_info(age),
    not missing_info(renewal_timing),
    not missing_info(last_renewal_method),
    missing_info(health_change).

next_question(ask_license_status) :-
    not missing_info(goal),
    not missing_info(age),
    not missing_info(renewal_timing),
    not missing_info(last_renewal_method),
    not missing_info(health_change),
    missing_info(license_status).

next_question(ask_outstanding_tickets_or_warrants) :-
    not missing_info(goal),
    not missing_info(age),
    not missing_info(renewal_timing),
    not missing_info(last_renewal_method),
    not missing_info(health_change),
    not missing_info(license_status),
    missing_info(outstanding_tickets_or_warrants).

next_question(ask_citizenship_for_online_renewal) :-
    not missing_info(goal),
    not missing_info(age),
    not missing_info(renewal_timing),
    not missing_info(last_renewal_method),
    not missing_info(health_change),
    not missing_info(license_status),
    not missing_info(outstanding_tickets_or_warrants),
    missing_info(citizenship_for_online_renewal).

next_question(ask_ssn_on_record) :-
    not missing_info(goal),
    not missing_info(age),
    not missing_info(renewal_timing),
    not missing_info(last_renewal_method),
    not missing_info(health_change),
    not missing_info(license_status),
    not missing_info(outstanding_tickets_or_warrants),
    not missing_info(citizenship_for_online_renewal),
    missing_info(ssn_on_record).

next_question(ask_front_card_changed) :-
    not missing_info(goal),
    not missing_info(age),
    not missing_info(renewal_timing),
    missing_info(front_card_changed).

next_question(ask_card_number_for_online_replacement) :-
    not missing_info(goal),
    not missing_info(front_card_changed),
    missing_info(card_number_for_online_replacement).

next_question(ask_date_of_birth_for_online_replacement) :-
    not missing_info(goal),
    not missing_info(front_card_changed),
    not missing_info(card_number_for_online_replacement),
    missing_info(date_of_birth_for_online_replacement).

next_question(ask_last4_ssn_for_online_replacement) :-
    not missing_info(goal),
    not missing_info(front_card_changed),
    not missing_info(card_number_for_online_replacement),
    not missing_info(date_of_birth_for_online_replacement),
    missing_info(last4_ssn_for_online_replacement).

next_question(ask_audit_number_for_online_replacement) :-
    not missing_info(goal),
    not missing_info(front_card_changed),
    not missing_info(card_number_for_online_replacement),
    not missing_info(date_of_birth_for_online_replacement),
    not missing_info(last4_ssn_for_online_replacement),
    missing_info(audit_number_for_online_replacement).

next_question(ask_residency_documents) :-
    not missing_info(goal),
    not missing_info(age),
    not missing_info(renewal_timing),
    not missing_info(front_card_changed),
    missing_info(residency_documents).

next_question(ask_identity_documents) :-
    not missing_info(goal),
    not missing_info(age),
    not missing_info(renewal_timing),
    not missing_info(front_card_changed),
    not missing_info(residency_documents),
    missing_info(identity_documents).

next_question(ask_social_security) :-
    not missing_info(goal),
    not missing_info(age),
    not missing_info(renewal_timing),
    not missing_info(front_card_changed),
    not missing_info(residency_documents),
    not missing_info(identity_documents),
    missing_info(social_security).

next_question(ask_lawful_presence_category) :-
    not missing_info(goal),
    not missing_info(age),
    not missing_info(renewal_timing),
    not missing_info(front_card_changed),
    not missing_info(residency_documents),
    not missing_info(identity_documents),
    not missing_info(social_security),
    missing_info(lawful_presence_category).

% --------------------------------------------------
% Defaults and exceptions
% --------------------------------------------------

online_renewal_eligible :-
    renewal_window_ok,
    last_renewed_in_person,
    under_79,
    health_conditions_unchanged,
    license_valid_status,
    no_outstanding_tickets_or_warrants,
    us_citizen,
    ssn_on_record.

service_mode(not_available_adult_flow) :-
    inferred_case(out_of_scope_under_18).

service_mode(in_person) :-
    application_case.

service_mode(cannot_renew_use_original_application_path) :-
    inferred_case(renewal),
    renewal_window_outside.

service_mode(may_be_online) :-
    inferred_case(renewal),
    online_renewal_eligible.

service_mode(likely_in_person) :-
    inferred_case(renewal),
    renewal_window_ok,
    not ab(d_renewal_likely_in_person),
    not -service_mode(likely_in_person).
ab(d_renewal_likely_in_person) :- online_renewal_eligible.
-service_mode(likely_in_person) :- online_renewal_eligible.

service_mode(online_mail_or_in_person) :-
    inferred_case(replacement),
    address_change_requested,
    not name_change_requested,
    not license_lost_stolen_damaged.

service_mode(in_person) :-
    inferred_case(replacement),
    license_stolen_and_fraud_used.

service_mode(in_person) :-
    inferred_case(replacement),
    front_of_card_info_changed,
    not address_change_requested.

service_mode(may_be_online) :-
    inferred_case(replacement),
    -front_card_changed,
    online_replacement_ready.

service_mode(likely_in_person) :-
    inferred_case(replacement),
    -front_card_changed,
    not ab(d_replacement_likely_in_person),
    not -service_mode(likely_in_person).
ab(d_replacement_likely_in_person) :- online_replacement_ready.
-service_mode(likely_in_person) :- online_replacement_ready.

% --------------------------------------------------
% Required documents / actions
% --------------------------------------------------

replacement_in_person_case :-
    inferred_case(replacement),
    service_mode(in_person).
replacement_in_person_case :-
    inferred_case(replacement),
    service_mode(likely_in_person).

required_doc(application_form) :- application_case.
required_doc(identity) :- application_case.
required_doc(citizenship_or_lawful_presence) :- application_case.
required_doc(social_security_number) :- application_case.
required_doc(texas_residency_two_documents) :- application_case.

required_doc(proof_of_insurance_for_each_owned_vehicle) :-
    application_case,
    owns_vehicle.

required_doc(texas_vehicle_registration_for_each_owned_vehicle) :-
    inferred_case(out_of_state_transfer),
    owns_vehicle.

required_doc(statement_no_vehicle_owned) :-
    application_case,
    -owns_vehicle.

required_doc(out_of_state_license_to_surrender) :-
    inferred_case(out_of_state_transfer),
    valid_unexpired_transfer_credential.

required_doc(adult_driver_education_certificate) :-
    inferred_case(first_time_application),
    age_18_to_24.

required_doc(impact_texas_drivers_certificate_within_90_days) :-
    inferred_case(first_time_application).

required_doc(most_recent_texas_license_and_audit_number) :-
    inferred_case(renewal),
    online_renewal_eligible.

required_doc(renewal_application_form) :-
    inferred_case(renewal),
    not online_renewal_eligible.

required_doc(identity) :-
    inferred_case(renewal),
    not online_renewal_eligible.

required_doc(citizenship_or_lawful_presence_if_not_on_record) :-
    inferred_case(renewal),
    not online_renewal_eligible,
    not lawful_presence_on_record.

required_doc(replacement_application_form) :-
    replacement_in_person_case.

required_doc(identity_one_primary_secondary_or_supporting_doc) :-
    replacement_in_person_case.

required_doc(citizenship_or_lawful_presence_if_not_previously_provided) :-
    replacement_in_person_case,
    not lawful_presence_on_record.

required_doc(social_security_if_not_previously_provided) :-
    replacement_in_person_case,
    not ssn_on_record.

required_doc(card_number_date_of_birth_last4_ssn_audit_number) :-
    inferred_case(replacement),
    -front_card_changed,
    online_replacement_ready.

% --------------------------------------------------
% Exams and waivers
% --------------------------------------------------

likely_exam(vision_exam) :- application_case.
likely_exam(vision_exam) :-
    inferred_case(renewal),
    not online_renewal_eligible.

likely_exam(knowledge_exam) :- inferred_case(first_time_application).
likely_exam(skills_exam) :- inferred_case(first_time_application).
likely_exam(impact_texas_drivers_before_skills_test) :- inferred_case(first_time_application).

likely_exam(knowledge_exam) :-
    inferred_case(out_of_state_transfer),
    not recognized_transfer_waiver_credential.

likely_exam(skills_exam) :-
    inferred_case(out_of_state_transfer),
    not recognized_transfer_waiver_credential.

likely_exam(no_knowledge_or_skills_exam_expected) :-
    inferred_case(out_of_state_transfer),
    recognized_transfer_waiver_credential.

waiver(residency_30_day_duration_waived) :-
    inferred_case(out_of_state_transfer),
    valid_unexpired_transfer_credential.

waiver(knowledge_exam_waived) :-
    inferred_case(out_of_state_transfer),
    recognized_transfer_waiver_credential.

waiver(skills_exam_waived) :-
    inferred_case(out_of_state_transfer),
    recognized_transfer_waiver_credential.

waiver(adult_driver_education_waived) :-
    inferred_case(out_of_state_transfer),
    recognized_transfer_waiver_credential,
    age(A),
    A >= 18.

waiver(impact_texas_drivers_waived) :-
    inferred_case(out_of_state_transfer),
    recognized_transfer_waiver_credential,
    age(A),
    A >= 18.

% --------------------------------------------------
% Explanation-friendly atoms
% --------------------------------------------------

explanation(under_18_out_of_scope) :-
    inferred_case(out_of_scope_under_18).

explanation(new_resident_with_out_of_state_license) :-
    inferred_case(out_of_state_transfer).

explanation(valid_or_recent_out_of_state_license_exam_waiver) :-
    inferred_case(out_of_state_transfer),
    recognized_transfer_waiver_credential.

explanation(transfer_requires_in_person_processing) :-
    inferred_case(out_of_state_transfer).

explanation(valid_unexpired_out_of_state_residency_30_day_waiver) :-
    inferred_case(out_of_state_transfer),
    valid_unexpired_transfer_credential.

explanation(first_time_application_requires_in_person_processing) :-
    inferred_case(first_time_application).

explanation(first_time_application_requires_tests) :-
    inferred_case(first_time_application).

explanation(age_18_to_24_requires_adult_driver_education) :-
    inferred_case(first_time_application),
    age_18_to_24.

explanation(renewal_window_is_two_years_before_or_after_expiration) :-
    inferred_case(renewal).

explanation(renewal_expired_more_than_two_years_cannot_be_renewed) :-
    inferred_case(renewal),
    renewal_window_outside.

explanation(online_renewal_requires_extra_eligibility_checks) :-
    inferred_case(renewal),
    renewal_window_ok.

explanation(replacement_without_front_card_changes_may_be_done_online) :-
    inferred_case(replacement),
    -front_card_changed.

explanation(replacement_front_of_card_changes_require_non_online_path) :-
    inferred_case(replacement),
    front_of_card_info_changed,
    not address_change_requested.

explanation(address_change_is_handled_as_replacement) :-
    inferred_case(replacement),
    address_change_requested.

explanation(stolen_fraudulent_card_should_be_reported_to_police) :-
    inferred_case(replacement),
    license_stolen_and_fraud_used.

% --------------------------------------------------
% Final guidance snippets
% --------------------------------------------------

final_guidance(under_15_no_ordinary_driver_license_path) :-
    inferred_case(out_of_scope_under_18),
    age(A),
    A < 15.

final_guidance(under_18_adult_license_not_available) :-
    inferred_case(out_of_scope_under_18).

final_guidance(drive_on_valid_out_of_state_license_for_up_to_90_days_after_moving) :-
    inferred_case(out_of_state_transfer),
    valid_unexpired_transfer_credential.

final_guidance(apply_in_person_and_surrender_out_of_state_license) :-
    inferred_case(out_of_state_transfer),
    valid_unexpired_transfer_credential.

final_guidance(out_of_state_transfer_exam_waivers_likely_apply) :-
    inferred_case(out_of_state_transfer),
    recognized_transfer_waiver_credential.

final_guidance(out_of_state_transfer_but_exam_waivers_not_certain) :-
    inferred_case(out_of_state_transfer),
    not recognized_transfer_waiver_credential.

final_guidance(first_time_application_in_person_with_docs_and_tests) :-
    inferred_case(first_time_application).

final_guidance(complete_adult_driver_education_before_applying) :-
    inferred_case(first_time_application),
    age_18_to_24,
    adult_driver_education_status(not_completed).

final_guidance(complete_adult_driver_education_before_applying) :-
    inferred_case(first_time_application),
    age_18_to_24,
    adult_driver_education_status(in_progress).

final_guidance(renewal_may_be_done_online_if_all_eligibility_rules_are_met) :-
    inferred_case(renewal),
    online_renewal_eligible.

final_guidance(renewal_likely_requires_in_person_if_online_rules_not_met) :-
    inferred_case(renewal),
    renewal_window_ok,
    not online_renewal_eligible.

final_guidance(license_expired_more_than_two_years_follow_original_application_guidance) :-
    inferred_case(renewal),
    renewal_window_outside.

final_guidance(replacement_may_be_done_online_if_no_front_changes_and_you_have_required_card_data) :-
    inferred_case(replacement),
    -front_card_changed,
    online_replacement_ready.

final_guidance(replacement_likely_requires_in_person_if_front_of_card_information_changed) :-
    inferred_case(replacement),
    front_of_card_info_changed,
    not address_change_requested.

final_guidance(address_must_be_changed_within_30_days_of_moving) :-
    inferred_case(replacement),
    address_change_requested.

final_guidance(address_change_can_be_online_mail_or_in_person_when_eligible) :-
    inferred_case(replacement),
    address_change_requested.

final_guidance(file_police_report_if_stolen_card_was_used_fraudulently) :-
    inferred_case(replacement),
    license_stolen_and_fraud_used.
