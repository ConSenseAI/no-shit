<?php
/**
 * Plugin Name: Mailpit SMTP sink wiring (fixture platform)
 * Description: Routes ALL WordPress mail into the leg's Mailpit sink over plain
 *              SMTP on the internal compose network. This is the FIXTURES §2.2
 *              msg-channel census coupling: every wp_mail() the host sends —
 *              WooCommerce order mail included — lands in the per-fixture sink,
 *              so presence AND absence claims can be made against sink
 *              checkpoints. No third-party SMTP plugin, no credentials.
 * Author:      No Shit fixture platform (PUBLIC, Apache-2.0)
 *
 * Loaded as a must-use plugin (bind-mounted read-only into
 * wp-content/mu-plugins/), so it cannot be deactivated from wp-admin and is
 * active from the first request onward.
 */

add_action(
    'phpmailer_init',
    static function ( $phpmailer ) {
        // Container env (compose sets these); defaults match the compose file.
        $host = getenv( 'NOSHIT_SMTP_HOST' );
        $port = getenv( 'NOSHIT_SMTP_PORT' );

        $phpmailer->isSMTP();
        $phpmailer->Host       = $host !== false && $host !== '' ? $host : 'mailpit';
        $phpmailer->Port       = $port !== false && $port !== '' ? (int) $port : 1025;
        $phpmailer->SMTPAuth   = false;   // sink accepts unauthenticated submission
        $phpmailer->SMTPSecure = '';      // plaintext on the internal network
        $phpmailer->SMTPAutoTLS = false;  // never attempt STARTTLS against the sink
    },
    PHP_INT_MAX // run last so nothing re-routes mail after us
);
