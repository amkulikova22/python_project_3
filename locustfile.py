from locust import HttpUser, task, between
import random
import string

def generate_random_url():
    return f"https://example.com/{''.join(random.choices(string.ascii_lowercase, k=10))}"

class ShortLinkUser(HttpUser):
    host = "http://localhost:8000"
    wait_time = between(1, 2)

    @task(3)
    def create_short_link(self):
        url = generate_random_url()
        with self.client.post("/links/shorten", json={"original_url": url}, catch_response=True) as response:
            if response.status_code == 201:
                response.success()
            else:
                response.failure(f"Failed to create link: {response.status_code}")

    @task(1)
    def redirect_to_link(self):
        url = generate_random_url()
        resp = self.client.post("/links/shorten", json={"original_url": url})
        if resp.status_code == 201:
            code = resp.json()["short_code"]
            self.client.get(f"/links/{code}", allow_redirects=False)