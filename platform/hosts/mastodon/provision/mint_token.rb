# noshit-f1-mastodon — mint an OAuth access token for a LOCAL account, headless.
#
# The reliable non-interactive path to an API token (no browser OAuth dance):
# a Doorkeeper application + a Doorkeeper::AccessToken bound to the account's
# user. Used for the OWNER's admin+write token (verification + admin ops).
#
# Run: bin/rails runner /provision/mint_token.rb <username> "<scopes>"
# Emits the raw token ONLY on a marked line (NOSHIT_TOKEN=...) that demo.sh
# captures into the gitignored .env and strips from any echoed output.
username = ARGV[0] or abort 'usage: mint_token.rb <username> <scopes(+ -separated)>'
# scopes are '+'-separated so a single ARGV survives shell/compose quoting.
scopes   = (ARGV[1] || 'read+write+admin:read+admin:write').tr('+', ' ')

acct = Account.find_local(username) or abort "no local account @#{username}"
user = acct.user or abort "no user for @#{username}"

# tootctl --confirmed confirms email but leaves `approved` false when the
# instance was ever in approval mode; an unapproved user's tokens are rejected
# ("login pending approval"). Ensure the owner is fully functional.
user.confirm unless user.confirmed?
user.update!(approved: true) unless user.approved?

app = Doorkeeper::Application.find_or_create_by!(name: 'noshit-f1-admin') do |a|
  a.redirect_uri = 'urn:ietf:wg:oauth:2.0:oob'
  a.scopes = 'read write follow admin:read admin:write'
end

token = Doorkeeper::AccessToken.create!(
  application: app,
  resource_owner_id: user.id,
  scopes: scopes,
  expires_in: nil,
  use_refresh_token: false,
)
puts "NOSHIT_TOKEN=#{token.token}"
warn "[mint_token] @#{username} (id=#{acct.id}) role=#{user.role&.name} scopes=#{scopes}"
