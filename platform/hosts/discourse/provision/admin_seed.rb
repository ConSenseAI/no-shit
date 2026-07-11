# noshit-f1-discourse — non-interactive admin + deterministic messaging state.
#
# Run INSIDE the launcher container as the discourse user:
#   docker exec -u discourse -w /var/www/discourse noshit-f1-discourse \
#     bash -lc 'bundle exec rails runner /shared/admin_seed.rb'
#
# setup.sh copies this file into the bind-mounted /shared dir (host:
# /home/user/fixture-runtime/discourse/shared/standalone) and writes the admin
# email to /shared/provision_email.txt (NOT a secret). This runner:
#   1. forces a deterministic site state (open registration, no approval, NO
#      welcome message, NO digests) so the signup->activation->absence proof is
#      not polluted by deferred/scheduled mail (FIXTURES §2.2 absence soundness);
#   2. lifts the app-level create-topic/post rate limits so the >=50-topic bulk
#      seed runs in one deterministic pass;
#   3. mints an ACTIVE admin (no UI, no interactive rake prompt) and a fresh
#      GLOBAL API key, written to /shared/api_key.txt (0600). The raw key is
#      printed nowhere; only a non-secret summary goes to stdout.
#
# Idempotent: re-running finds the existing admin and rotates the demo API key.

def set_setting(name, value)
  unless SiteSetting.respond_to?("#{name}=")
    puts "  - skip (absent in this version): #{name}"
    return
  end
  SiteSetting.public_send("#{name}=", value)
  puts "  - #{name} = #{value.inspect}"
rescue => e
  puts "  - skip (#{name}): #{e.class}: #{e.message}"
end

puts "== admin_seed: Discourse #{Discourse::VERSION::STRING} =="

puts "[settings] registration + messaging determinism:"
set_setting(:allow_new_registrations, true)
set_setting(:must_approve_users, false)
set_setting(:enable_local_logins, true)
set_setting(:login_required, false)
set_setting(:send_welcome_message, false)      # no welcome PM/email after activation
set_setting(:disable_digest_emails, true)      # no scheduled digest mail
set_setting(:default_email_digest_frequency, 0)  # 0 = never (belt & suspenders)
set_setting(:notification_email, "noreply@noshit.test")
# validation thresholds relaxed so short deterministic seed content is accepted
set_setting(:min_topic_title_length, 5)
set_setting(:min_post_length, 5)
set_setting(:min_first_post_length, 5)
set_setting(:body_min_entropy, 0)
set_setting(:title_min_entropy, 0)

puts "[settings] lift create rate limits for the deterministic bulk seed:"
set_setting(:rate_limit_create_topic, 0)
set_setting(:rate_limit_create_post, 0)
set_setting(:unique_posts_mins, 0)
set_setting(:max_topics_per_day, 1000)
set_setting(:max_topics_in_first_day, 1000)

email = File.read("/shared/provision_email.txt").strip
username = "noshit_admin"
puts "[admin] ensuring active admin for #{email} (username #{username})"

u = User.find_by_email(email)
unless u
  u = User.new(
    email: email,
    username: username,
    name: "NoShit F1 Admin",
    password: SecureRandom.hex(20),   # random, discarded — admin acts via API key
  )
  u.save!(validate: false)
end
u.update_columns(active: true, approved: true, approved_at: Time.now, trust_level: TrustLevel[4])
u.activate rescue nil                  # confirm email token, mark active
u.email_tokens.update_all(confirmed: true) rescue nil
u.grant_admin! unless u.admin?
u.reload
puts "  - user ##{u.id} username=#{u.username} active=#{u.active?} admin=#{u.admin?} approved=#{u.approved?}"

# Fresh global API key (rotate any prior demo key). Raw key available only now.
# Emitted on a MARKED line for the orchestrator (demo.sh) to capture into the
# gitignored .env (0600). demo.sh strips this line before echoing anything, so
# the key is never displayed or logged. uid-independent (no bind-mount write).
ApiKey.where(description: "noshit-f1-demo").find_each(&:destroy!)
key = ApiKey.create!(description: "noshit-f1-demo", created_by_id: u.id)
puts "NOSHIT_APIKEY=#{key.key}"
puts "  - minted global API key (description=noshit-f1-demo); captured by demo.sh -> .env"

# Proof-5 corroboration at the Ruby layer: the bundled subscriptions plugin is
# loaded into this process. demo.py independently confirms via the admin API.
subs = Discourse.plugins.map { |p| p.name rescue p.metadata&.name }.compact.grep(/subscription/i)
puts "[plugin] loaded plugins matching /subscription/i: #{subs.inspect}"

puts "== admin_seed: done =="
