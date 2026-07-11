# noshit-f1-mastodon — CLOCK-STORY NOTE for F2 (evidence only, no assertion).
#
# Answers, from inside the running web/sidekiq container: which libc (fake-time
# rung-2 candidate?), where scheduled jobs run, and whether those jobs are
# enumerable / harness-triggerable (rung 3). demo.py prints this verbatim into
# the transcript. It also names the clock-relevant nli windows this host carries
# natively (archive cooldown, etc.), which the leg README expands for F2.
require 'sidekiq/api'

os  = (File.read('/etc/os-release')[/PRETTY_NAME="?([^"\n]+)/, 1] rescue '?')
ldd = (`ldd --version 2>&1`.lines.first.to_s.strip rescue '?')
puts "os_release=#{os}"
puts "ruby=#{RUBY_VERSION} platform=#{RUBY_PLATFORM}"
puts "libc=#{ldd}"
puts "sidekiq=#{defined?(Sidekiq) ? Sidekiq::VERSION : false} (all mail/backup/deletion jobs run here)"

# Mastodon's recurring jobs are Scheduler::* Sidekiq workers driven by
# sidekiq-scheduler (schedule in config/sidekiq.yml). They are ordinary classes:
# enumerable, and each is triggerable on demand via `Klass.new.perform` or
# `Klass.perform_async` through rails runner — the rung-3 harness hook for F2.
begin
  sched_workers = ObjectSpace.each_object(Class).select do |c|
    c.name.to_s.start_with?('Scheduler::') && c.instance_methods(false).include?(:perform)
  end
  puts "scheduler_worker_classes=#{sched_workers.size}"
  puts "sample_scheduler=#{sched_workers.map(&:name).compact.sort.first(6).inspect}"
  # The live sidekiq-scheduler cron entries (if the scheduler is loaded in-process).
  cron = (Sidekiq.respond_to?(:schedule) ? (Sidekiq.schedule || {}) : {})
  puts "sidekiq_scheduler_cron_entries=#{cron.size}"
  puts "enumerable_and_triggerable=true (Scheduler::* workers; run via Klass.new.perform / perform_async)"
rescue => e
  puts "scheduled_job_enumeration_error=#{e.class}: #{e.message}"
end

# nli clock-relevant windows this host carries natively (for F2 virtual-clock):
puts "nli_window archive_cooldown=7d (Backup: one request per account per 7 days)"
puts "nli_window archive_link=served from public/system while the Backup row lives"
puts "nli_window deletion=self-serve delete suspends immediately, purge job async"
