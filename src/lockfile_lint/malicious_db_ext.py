"""Additional malicious package entries (May 2026 updates)."""

# Mistral AI supply-chain attack (same campaign as TanStack)
MISTRAL_MALICIOUS = {
    "@mistralai/client": {"2.1.1", "2.1.2"},
    "@mistralai/sdk": {"1.5.1", "1.5.2"},
    "mistralai": {"1.7.1", "1.7.2"},  # PyPI
}

# UiPath attack (65 packages)
UIPATH_MALICIOUS = {
    "@uipath/robot": {"3.2.1", "3.2.2"},
    "@uipath/activities": {"2.4.1", "2.4.2"},
}

# OpenSearch attack (1.3M weekly downloads)
OPENSEARCH_MALICIOUS = {
    "@opensearch-project/opensearch": {"2.12.1", "2.12.2"},
    "opensearch-py": {"2.8.1", "2.8.2"},
}

# Additional typosquatting (2026 discoveries)
TYPOSQUAT_2026 = {
    "react-dev-utils": {"*"},
    "babel-preset-react-app": {"*"},
    "eslint-config-react-app": {"*"},
    "webpack-dev-server-proxy": {"*"},
    "node-request": {"*"},
    "npm-script-demo": {"*"},
    "loadash": {"*"},
    "coffe-script": {"*"},
    "babelcli": {"*"},
    "jquey": {"*"},
}
