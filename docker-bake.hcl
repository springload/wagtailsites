// this is registry used for caching purposes only
variable "CACHE_REGISTRY" { default = "" }
// this is remote registry to push to
variable "REGISTRY" { default = "" }
variable "ENVIRONMENT" { default = "preview" }
variable "PROJECT" { default = "madewithwagtail" }
variable "VERSION" { default = "latest" }

// targets in groups are built in parallel
group "default" {
  targets = ["app", "httpd"]
}

target "base" {
  dockerfile = "docker/application/Dockerfile"
  target     = "base"
  cache-from = notequal("", CACHE_REGISTRY) ? ["type=registry,ref=${CACHE_REGISTRY}/base:${VERSION}", "type=registry,ref=${CACHE_REGISTRY}/base:cache"] : []
  cache-to   = notequal("", CACHE_REGISTRY) ? ["type=registry,ref=${CACHE_REGISTRY}/base:cache,mode=max"] : []
}

target "app" {
  dockerfile = "docker/application/Dockerfile"
  target     = "app"
  cache-from = notequal("", CACHE_REGISTRY) ? ["type=registry,ref=${CACHE_REGISTRY}/app:${VERSION}", "type=registry,ref=${CACHE_REGISTRY}/app:cache"] : []
  cache-to   = notequal("", CACHE_REGISTRY) ? ["type=registry,ref=${CACHE_REGISTRY}/app:cache,mode=max"] : []

  args = {
    VERSION : VERSION,
  }

  tags = notequal("", REGISTRY) ? [
    "${REGISTRY}/${PROJECT}-app:${ENVIRONMENT}-latest",
    "${REGISTRY}/${PROJECT}-app:${ENVIRONMENT}-${VERSION}",
    "${REGISTRY}/${PROJECT}-app:common-${VERSION}",
  ] : []
}

target "app-test" {
  dockerfile = "docker/application/Dockerfile"
  target     = "app-test"
  cache-from = notequal("", CACHE_REGISTRY) ? ["type=registry,ref=${CACHE_REGISTRY}/app-test:${VERSION}", "type=registry,ref=${CACHE_REGISTRY}/app-test:cache"] : []
  cache-to   = notequal("", CACHE_REGISTRY) ? ["type=registry,ref=${CACHE_REGISTRY}/app-test:cache,mode=max"] : []

  args = {
    VERSION : VERSION,
  }

  // this tag is different as we're going to load it
  tags = ["${PROJECT}/app-test:${VERSION}"]
}

target "tasks" {
  dockerfile = "docker/application/Dockerfile"
  target     = "tasks"
  cache-from = notequal("", CACHE_REGISTRY) ? ["type=registry,ref=${CACHE_REGISTRY}/tasks:${VERSION}", "type=registry,ref=${CACHE_REGISTRY}/tasks:cache"] : []
  cache-to   = notequal("", CACHE_REGISTRY) ? ["type=registry,ref=${CACHE_REGISTRY}/tasks:cache,mode=max"] : []

  args = {
    VERSION : VERSION,
  }

  tags = notequal("", REGISTRY) ? [
    "${REGISTRY}/${PROJECT}-tasks:${ENVIRONMENT}-latest",
    "${REGISTRY}/${PROJECT}-tasks:${ENVIRONMENT}-${VERSION}",
    "${REGISTRY}/${PROJECT}-tasks:common-${VERSION}",
  ] : []
}

target "httpd" {
  context = "docker/httpd"

  cache-from = notequal("", CACHE_REGISTRY) ? ["type=registry,ref=${CACHE_REGISTRY}/httpd:${ENVIRONMENT}-${VERSION}", "type=registry,ref=${CACHE_REGISTRY}/httpd:cache"] : []
  cache-to   = notequal("", CACHE_REGISTRY) ? ["type=registry,ref=${CACHE_REGISTRY}/httpd:cache,mode=max"] : []

  args = {
    VERSION : VERSION,
  }

  tags = notequal("", REGISTRY) ? [
    "${REGISTRY}/${PROJECT}-httpd:${ENVIRONMENT}-latest",
    "${REGISTRY}/${PROJECT}-httpd:${ENVIRONMENT}-${VERSION}",
    "${REGISTRY}/${PROJECT}-httpd:common-${VERSION}",
  ] : []
}
