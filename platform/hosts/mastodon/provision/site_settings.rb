# noshit-f1-mastodon — deterministic instance state for the proofs.
#
# Run via: docker compose exec -T web bin/rails runner /provision/site_settings.rb
#
# Opens registration (the signup->confirmation->absence proof needs the real
# public /auth flow) with NO approval step, so confirmation mail is the only
# gate. Everything else Mastodon does not send unsolicited by default (no
# digests/marketing), so the sink stays a clean transactional census — the
# absence windows anchor to sidekiq drain, not to muting scheduled mail.
# Idempotent.
Setting.registrations_mode = 'open'
Setting.site_contact_email = ENV.fetch('MASTO_OWNER_EMAIL', 'owner@localhost')
Setting.site_contact_username = ENV.fetch('MASTO_OWNER_USERNAME', 'noshit_owner')
# Belt & suspenders: no closed-beta invite gate, no age gate for the fixture.
Setting.min_age = 0 if Setting.respond_to?(:min_age=)

puts "registrations_mode=#{Setting.registrations_mode}"
puts "site_contact=@#{Setting.site_contact_username} <#{Setting.site_contact_email}>"
