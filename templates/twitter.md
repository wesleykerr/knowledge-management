---
content-type: tweet
tweet_id: {{id}}
url: {{url}}
author: {{author.name}} (@{{author.username}})
date: {{tweet_date}}
added_date: {{today}}
tags:
---

# Tweet by @{{author.username}}

{% if screenshot %}
![[{{screenshot}}]]
{% endif %}

{{text}}

{% if media %}
## Media
{% for image in media %}
![[{{image}}]]
{% endfor %}
{% endif %}

{% if video_url %}
## Video
[Watch Video]({{video_url}})
{% endif %}

[View on Twitter]({{url}})

Created: {{tweet_date}}
Added: {{today}}