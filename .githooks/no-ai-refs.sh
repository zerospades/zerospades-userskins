#!/bin/bash
# Shared matcher: does a piece of text reference Claude or AI?
#
# Sourced by commit-msg and pre-push so both agree on the patterns.
#
# The acronym is matched case-SENSITIVELY as "AI", on purpose. A
# case-insensitive "ai" matches main, fail, detail, email, available and the
# French "j'ai", which makes the hook useless. Everything else is
# case-insensitive, since "Claude" and "claude" are both references.

# Case-insensitive: names, products and attribution trailers.
AI_PATTERNS_I='claude|anthropic|copilot|chatgpt|openai|gemini|artificial[ -]intelligence|co-authored-by|generated with|🤖'

# Case-sensitive: bare acronyms only, so ordinary words are left alone.
AI_PATTERNS_S='(^|[^[:alnum:]'"'"'’])(AI|A\.I\.|LLM)([^[:alnum:]'"'"'’]|$)'

# Prints the offending lines and returns 0 when the text references AI.
ai_refs_in() {
	local file="$1" found=1
	if grep -niE "$AI_PATTERNS_I" -- "$file"; then
		found=0
	fi
	if grep -nE "$AI_PATTERNS_S" -- "$file"; then
		found=0
	fi
	return $found
}
