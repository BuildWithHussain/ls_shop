module.exports = {
	extends: ['@commitlint/config-conventional'],
	rules: {
		// `merge:` is this repo's own subject for folding one feature branch into another.
		// Real git merge commits are already ignored by commitlint's defaults; these are not.
		'type-enum': [
			2,
			'always',
			[
				'build',
				'chore',
				'ci',
				'docs',
				'feat',
				'fix',
				'merge',
				'perf',
				'refactor',
				'revert',
				'style',
				'test',
			],
		],
	},
}
