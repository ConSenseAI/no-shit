# noshit-f1-discourse — CLOCK-STORY NOTE for F2 (evidence only, no assertion).
#
# Answers, from inside the running container: which libc (fake-time rung-2
# candidate?), where scheduled jobs run, and whether those jobs are enumerable /
# harness-triggerable (rung 3). demo.py prints this verbatim into the transcript.
os = (File.read("/etc/os-release")[/PRETTY_NAME="?([^"\n]+)/, 1] rescue "?")
ldd = (`ldd --version 2>&1`.lines.first.to_s.strip rescue "?")
puts "os_release=#{os}"
puts "ruby=#{RUBY_VERSION} platform=#{RUBY_PLATFORM}"
puts "libc=#{ldd}"
puts "sidekiq=#{defined?(Sidekiq) ? Sidekiq::VERSION : false} (scheduled jobs run in the in-container sidekiq)"
puts "mini_scheduler=#{defined?(MiniScheduler) ? true : false} (Discourse's periodic-job driver)"

# Scheduled jobs are ordinary classes: enumerable, and each is triggerable on
# demand via `Jobs.enqueue(Klass)` or `Klass.new.execute({})` through rails
# runner — the rung-3 harness hook for F2.
begin
  sched = ObjectSpace.each_object(Class).select { |c| c < ::Jobs::Scheduled }
  puts "scheduled_job_classes=#{sched.size}"
  puts "sample_scheduled=#{sched.map(&:name).compact.sort.first(6).inspect}"
  puts "enumerable_and_triggerable=true (Jobs::Scheduled subclasses; run via Jobs.enqueue / Klass.new.execute)"
rescue => e
  puts "scheduled_job_enumeration_error=#{e.class}: #{e.message}"
end
