# noshit-f1-mastodon — set a known password + mint a write token for a batch of
# LOCAL accounts (created just before this by `tootctl accounts create`).
#
# WHY a known password: the CSV export (settings), archive request (settings),
# and account deletion (settings) are all SESSION/cookie web flows — the demo
# must be able to web-login as these accounts. tootctl generates a random
# password it prints once; instead of parsing/threading those, we set one shared
# known password (MASTO_SEED_PASSWORD from .env) so re-runs stay deterministic.
# A write token is minted in the same pass so seeding can post statuses via the
# REST API as each account.
#
# Run: bin/rails runner /provision/prepare_accounts.rb "user1,user2,..." <password> "<scopes>"
# Emits one marked line per account: NOSHIT_TOKEN=<username>:<token>:<account_id>
usernames = ARGV[0].to_s.split(',').map(&:strip).reject(&:empty?)
password  = ARGV[1] or abort 'usage: prepare_accounts.rb u1,u2 <password> <scopes(+ -sep)>'
# scopes are '+'-separated so a single ARGV survives shell/compose quoting.
scopes    = (ARGV[2] || 'read+write+follow').tr('+', ' ')
abort 'no usernames given' if usernames.empty?

app = Doorkeeper::Application.find_or_create_by!(name: 'noshit-f1-seed') do |a|
  a.redirect_uri = 'urn:ietf:wg:oauth:2.0:oob'
  a.scopes = 'read write follow'
end

usernames.each do |u|
  acct = Account.find_local(u)
  unless acct && acct.user
    warn "[prepare] MISSING @#{u} (no local account/user)"
    next
  end
  user = acct.user
  user.password = password
  user.password_confirmation = password
  user.confirm unless user.confirmed?
  user.update!(approved: true)
  token = Doorkeeper::AccessToken.create!(
    application: app,
    resource_owner_id: user.id,
    scopes: scopes,
    expires_in: nil,
    use_refresh_token: false,
  )
  puts "NOSHIT_TOKEN=#{u}:#{token.token}:#{acct.id}"
  warn "[prepare] @#{u} id=#{acct.id} confirmed=#{user.confirmed?} approved=#{user.approved?}"
end
