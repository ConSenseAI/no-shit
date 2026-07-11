<?php
/**
 * noshit-f1-woocommerce — deterministic store configuration (idempotent).
 * Run inside the wpcli container:  wp eval-file /seed/configure-store.php
 *
 * Everything a checkout needs and nothing external: USD, guest checkout,
 * shipping disabled (digital-goods store), the built-in OFFLINE Cash-on-
 * delivery gateway (FIXTURES §2.3 payment spine: "WooCommerce's test
 * gateway"), and the CLASSIC shortcode cart/checkout pages so the documented
 * plain-HTTP path (?wc-ajax=checkout + form nonce) is the checkout surface.
 */

if ( ! class_exists( 'WooCommerce' ) ) {
	WP_CLI::error( 'WooCommerce is not active — run install.sh first.' );
}

// -- storefront live (WooCommerce 9.1+ ships new stores in "coming soon" mode).
update_option( 'woocommerce_coming_soon', 'no' );
update_option( 'woocommerce_store_pages_only', 'no' );

// -- basics: USD, US store, no taxes, no tracking, skip onboarding nags.
update_option( 'woocommerce_currency', 'USD' );
update_option( 'woocommerce_default_country', 'US:CA' );
update_option( 'woocommerce_calc_taxes', 'no' );
update_option( 'woocommerce_allow_tracking', 'no' );
update_option( 'woocommerce_show_marketplace_suggestions', 'no' );
update_option( 'woocommerce_onboarding_profile', array( 'skipped' => true ) );

// -- digital-goods-friendly: shipping disabled entirely; guest checkout on.
update_option( 'woocommerce_ship_to_countries', 'disabled' );
update_option( 'woocommerce_enable_guest_checkout', 'yes' );
update_option( 'woocommerce_enable_checkout_login_reminder', 'no' );

// -- offline payment gateway: Cash on delivery (no external processor).
//    enable_for_virtual must stay 'yes' or COD hides on virtual-only carts.
update_option(
	'woocommerce_cod_settings',
	array(
		'enabled'            => 'yes',
		'title'              => 'Cash on delivery',
		'description'        => 'Offline test gateway (fixture platform payment spine).',
		'instructions'       => '',
		'enable_for_methods' => array(),
		'enable_for_virtual' => 'yes',
	)
);

// -- classic (shortcode) cart + checkout pages. New WooCommerce installs ship
//    BLOCK cart/checkout (Store-API driven); the classic shortcodes remain
//    fully supported and give the deterministic ?wc-ajax=checkout form path
//    this leg's E2 proof exercises. Recorded as a finding in the README.
if ( wc_get_page_id( 'cart' ) < 1 || wc_get_page_id( 'checkout' ) < 1 ) {
	WC_Install::create_pages();
}
$cart_id     = wc_get_page_id( 'cart' );
$checkout_id = wc_get_page_id( 'checkout' );
wp_update_post(
	array(
		'ID'           => $cart_id,
		'post_content' => '<!-- wp:shortcode -->[woocommerce_cart]<!-- /wp:shortcode -->',
		'post_status'  => 'publish',
	)
);
wp_update_post(
	array(
		'ID'           => $checkout_id,
		'post_content' => '<!-- wp:shortcode -->[woocommerce_checkout]<!-- /wp:shortcode -->',
		'post_status'  => 'publish',
	)
);

echo 'store configured: currency=' . get_option( 'woocommerce_currency' )
	. ' country=' . get_option( 'woocommerce_default_country' )
	. ' shipping=' . get_option( 'woocommerce_ship_to_countries' )
	. ' coming_soon=' . get_option( 'woocommerce_coming_soon' ) . "\n";
$cod = get_option( 'woocommerce_cod_settings' );
echo 'cod gateway: enabled=' . $cod['enabled'] . ' enable_for_virtual=' . $cod['enable_for_virtual'] . "\n";
echo 'classic pages: cart_page_id=' . $cart_id . ' checkout_page_id=' . $checkout_id . " (shortcode content)\n";
