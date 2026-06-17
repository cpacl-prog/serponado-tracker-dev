GITHUB_TOKEN ?= $(shell cat .github_token 2>/dev/null)
REPO         := cpacl-prog/serponado-tracker-dev

trigger:
	@test -n "$(GITHUB_TOKEN)" || (echo "❌ GITHUB_TOKEN nicht gesetzt" && exit 1)
	curl -s -o /dev/null -w "%{http_code}" \
		-X POST \
		-H "Authorization: token $(GITHUB_TOKEN)" \
		-H "Accept: application/vnd.github+json" \
		https://api.github.com/repos/$(REPO)/dispatches \
		-d '{"event_type":"fetch-rankings"}' | grep -q "^204$$" \
		&& echo "✅ Workflow gestartet" \
		|| echo "❌ Fehler beim Trigger"

.PHONY: trigger
