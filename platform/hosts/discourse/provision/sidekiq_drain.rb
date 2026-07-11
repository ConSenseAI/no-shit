# noshit-f1-discourse — drain the Sidekiq mail path to its OBSERVABLE completion.
#
# Discourse sends all mail through Sidekiq jobs. Absence windows must anchor to a
# completed-delivery EVENT, not a wall-clock timer (FIXTURES §2.2 0.1.3). demo.py
# calls this after the activation mail has landed, to wait until the immediate
# queue is empty and no worker is busy — i.e. the mailer jobs have actually run —
# before it opens the absence window. Bounded so it can never hang the demo.
require "sidekiq/api"

deadline = Time.now + 45
loop do
  s = Sidekiq::Stats.new
  busy = Sidekiq::Workers.new.size
  break if s.enqueued.to_i.zero? && busy.to_i.zero?
  break if Time.now > deadline
  sleep 1
end

s = Sidekiq::Stats.new
puts "enqueued=#{s.enqueued} busy=#{Sidekiq::Workers.new.size} " \
     "scheduled=#{Sidekiq::ScheduledSet.new.size} retries=#{Sidekiq::RetrySet.new.size} " \
     "processed=#{s.processed} failed=#{s.failed}"
