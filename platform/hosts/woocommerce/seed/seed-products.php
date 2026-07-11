<?php
/**
 * noshit-f1-woocommerce — SEEDING PROOF (FIXTURES §2.3: bulk content,
 * hundreds-per-collection). Seeds >=120 published virtual products across
 * >=3 product categories in ONE deterministic pass. Run (the one command):
 *
 *   wp eval-file /seed/seed-products.php        (seed.sh wraps this and
 *                                                records the wall-time)
 *
 * Deterministic: fixed category set, SKU-indexed names, prices a pure
 * function of the index. Idempotent: SKUs already present are skipped, so a
 * re-run against a seeded store creates nothing and reports skipped=132.
 */

if ( ! class_exists( 'WooCommerce' ) ) {
	WP_CLI::error( 'WooCommerce is not active — run install.sh first.' );
}

$t0 = microtime( true );

$plan = array(
	'E-Books'  => array( 'slug' => 'e-books',  'prefix' => 'F1-EBK', 'name' => 'Field Notes Vol. %03d',    'base' => 4 ),
	'Software' => array( 'slug' => 'software', 'prefix' => 'F1-SFT', 'name' => 'Utility Suite Build %03d', 'base' => 9 ),
	'Music'    => array( 'slug' => 'music',    'prefix' => 'F1-MUS', 'name' => 'Session Tape No. %03d',    'base' => 6 ),
);
$per_category = 44; // 3 x 44 = 132 >= 120

wp_defer_term_counting( true );

$created = 0;
$skipped = 0;
foreach ( $plan as $cat_name => $c ) {
	$term = term_exists( $c['slug'], 'product_cat' );
	if ( ! $term ) {
		$term = wp_insert_term( $cat_name, 'product_cat', array( 'slug' => $c['slug'] ) );
		if ( is_wp_error( $term ) ) {
			WP_CLI::error( 'category create failed: ' . $term->get_error_message() );
		}
	}
	$term_id = (int) ( is_array( $term ) ? $term['term_id'] : $term );

	for ( $i = 1; $i <= $per_category; $i++ ) {
		$sku = sprintf( '%s-%03d', $c['prefix'], $i );
		if ( wc_get_product_id_by_sku( $sku ) ) {
			$skipped++;
			continue;
		}
		$p = new WC_Product_Simple();
		$p->set_name( sprintf( $c['name'], $i ) );
		$p->set_sku( $sku );
		// price = pure function of index: deterministic across runs.
		$p->set_regular_price( sprintf( '%d.%02d', $c['base'] + ( $i % 20 ), ( $i * 7 ) % 100 ) );
		$p->set_virtual( true ); // digital goods — no shipping anywhere in the flow
		$p->set_catalog_visibility( 'visible' );
		$p->set_status( 'publish' );
		$p->set_category_ids( array( $term_id ) );
		$p->save();
		$created++;
	}
}

wp_defer_term_counting( false );

$elapsed = microtime( true ) - $t0;
$total   = (int) wp_count_posts( 'product' )->publish;

printf( "seed pass: created=%d skipped=%d elapsed_in_wp=%.1fs\n", $created, $skipped, $elapsed );
printf( "published products total: %d\n", $total );
$cats = get_terms( array( 'taxonomy' => 'product_cat', 'hide_empty' => true ) );
$nonempty = 0;
foreach ( $cats as $t ) {
	if ( 'uncategorized' === $t->slug ) {
		continue;
	}
	printf( "  category %-10s products=%d\n", $t->slug, (int) $t->count );
	$nonempty++;
}

if ( $total < 120 ) {
	WP_CLI::error( "seeding proof FAILED: only $total published products (need >=120)" );
}
if ( $nonempty < 3 ) {
	WP_CLI::error( "seeding proof FAILED: only $nonempty non-empty categories (need >=3)" );
}
WP_CLI::success( "seeding proof: $total products across $nonempty categories in one pass" );
