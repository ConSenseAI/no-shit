# noshit-f1-mastodon — drain the Sidekiq mail/work path to OBSERVABLE completion.
#
# Mastodon sends every mail (confirmation, archive-ready) and runs every account
# archive (BackupWorker) and deletion (DeleteAccountService) through Sidekiq.
# Absence windows must anchor to a completed-delivery EVENT, not a wall-clock
# timer (FIXTURES §2.2 0.1.3). demo.py calls this after the action-under-test to
# wait until the immediate queues are empty and no worker is busy — i.e. the
# mailer/backup/deletion jobs have actually run — before opening the absence
# window. Bounded so it can never hang the demo.
#
# NOTE: the sidekiq SCHEDULED set (future-dated periodic jobs — Mastodon's
# Scheduler::* recurring workers) is deliberately NOT part of the anchor; it is a
# forward calendar, not pending mail. The anchor is enqueued (immediate) + busy.
require 'sidekiq/api'

deadline = Time.now + (ARGV[0] ? ARGV[0].to_i : 60)
loop do
  stats = Sidekiq::Stats.new
  busy  = Sidekiq::Workers.new.size
  break if stats.enqueued.to_i.zero? && busy.to_i.zero?
  break if Time.now > deadline
  sleep 1
end

stats = Sidekiq::Stats.new
puts "enqueued=#{stats.enqueued} busy=#{Sidekiq::Workers.new.size} " \
     "scheduled=#{Sidekiq::ScheduledSet.new.size} retries=#{Sidekiq::RetrySet.new.size} " \
     "processed=#{stats.processed} failed=#{stats.failed}"
