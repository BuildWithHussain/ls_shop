/* Pixio authors its carousels for Swiper and slick; both are banned here, so the swiper-*
   and slick-* class names are kept for style.css and driven by Embla instead.

   Two consequences of that swap are handled below and nowhere else: Swiper sizes its slides
   in JS (Embla does not, so every slide width lives in pixio.css), and style.css keys real
   visual state off swiper-slide-active / swiper-slide-visible / slick-current, which Swiper
   and slick used to stamp on. */
(() => {
	const carousels_by_name = new Map();

	function set_slide_state(embla) {
		const slides = embla.slideNodes();
		const selected = embla.selectedScrollSnap();
		const in_view = embla.slidesInView();

		for (const [index, slide] of slides.entries()) {
			slide.classList.toggle('swiper-slide-active', index === selected);
			slide.classList.toggle('swiper-slide-prev', index === selected - 1);
			slide.classList.toggle('swiper-slide-next', index === selected + 1);
			slide.classList.toggle('swiper-slide-visible', in_view.includes(index));
			slide.classList.toggle('slick-current', index === selected);
			slide.classList.toggle('slick-active', in_view.includes(index));
		}
	}

	function add_navigation(embla, name) {
		for (const button of document.querySelectorAll(
			`[data-carousel-prev="${name}"]`,
		)) {
			button.addEventListener('click', () => {
				embla.scrollPrev();
			});
		}
		for (const button of document.querySelectorAll(
			`[data-carousel-next="${name}"]`,
		)) {
			button.addEventListener('click', () => {
				embla.scrollNext();
			});
		}
	}

	function add_sync(embla, partner_name) {
		const partner = carousels_by_name.get(partner_name);
		if (!partner) {
			return;
		}
		/* Both directions are wired the first time the pair is complete, and each hop is
		   guarded on the index already matching so the two do not ping-pong. */
		embla.on('select', () => {
			const index = embla.selectedScrollSnap();
			if (partner.selectedScrollSnap() !== index) {
				partner.scrollTo(index);
			}
		});
		partner.on('select', () => {
			const index = partner.selectedScrollSnap();
			if (embla.selectedScrollSnap() !== index) {
				embla.scrollTo(index);
			}
		});
	}

	function add_carousel(root) {
		const options = {
			loop: root.dataset.carouselLoop === 'true',
			align: root.dataset.carouselAlign || 'start',
			direction: getComputedStyle(document.body).direction,
			slidesToScroll: 1,
		};
		const embla = EmblaCarousel(root, options);
		const name = root.dataset.pixioCarousel;

		carousels_by_name.set(name, embla);
		embla.on('init', () => {
			set_slide_state(embla);
		});
		embla.on('select', () => {
			set_slide_state(embla);
		});
		/* .swiper-visible fades every slide it does not consider visible, and Embla only knows
		   which those are once it has measured - after this handler is wired, not before. */
		embla.on('slidesInView', () => {
			set_slide_state(embla);
		});
		embla.on('reInit', () => {
			set_slide_state(embla);
		});
		set_slide_state(embla);
		add_navigation(embla, name);
		return embla;
	}

	function add_carousels() {
		if (typeof EmblaCarousel !== 'function') {
			return;
		}
		const roots = Array.from(
			document.querySelectorAll('[data-pixio-carousel]'),
		);
		for (const root of roots) {
			add_carousel(root);
		}
		for (const root of roots) {
			if (root.dataset.carouselSync) {
				add_sync(
					carousels_by_name.get(root.dataset.pixioCarousel),
					root.dataset.carouselSync,
				);
			}
		}
	}

	if (document.readyState === 'loading') {
		document.addEventListener('DOMContentLoaded', add_carousels);
	} else {
		add_carousels();
	}
})();
