/* Pixio's markup carries `class="wow fadeInUp" data-wow-delay="..."` on ~94 homepage
   elements. animate.css v3 only runs the keyframes once `.animated` is also present, and
   upstream adds it with wow.js + jQuery. This is that trigger on IntersectionObserver.
   Elements are hidden by this script and not by CSS, so a failed load degrades to no
   animation instead of an invisible page. */
(() => {
	const observer = new IntersectionObserver(
		(entries) => {
			for (const entry of entries) {
				if (!entry.isIntersecting) {
					continue;
				}
				const element = entry.target;
				element.style.animationDelay = element.dataset.wowDelay || '';
				element.classList.add('animated');
				element.style.visibility = 'visible';
				observer.unobserve(element);
			}
		},
		{ rootMargin: '0px 0px -10% 0px' },
	);

	function add_wow_animations() {
		for (const element of document.querySelectorAll('.wow')) {
			element.style.visibility = 'hidden';
			observer.observe(element);
		}
	}

	if (document.readyState === 'loading') {
		document.addEventListener('DOMContentLoaded', add_wow_animations);
	} else {
		add_wow_animations();
	}
})();
