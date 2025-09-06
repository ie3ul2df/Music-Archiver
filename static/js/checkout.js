// --------------------------- static/js/checkout.js --------------------------- //
document.addEventListener("DOMContentLoaded", () => {
  const stripe = Stripe(stripePublicKey); // passed via context processor if you prefer
  const elements = stripe.elements();
  const card = elements.create("card", { style: { base: { fontSize: "16px" } } });
  card.mount("#card-element");

  card.on("change", (event) => {
    document.getElementById("card-errors").textContent = event.error ? event.error.message : "";
  });

  const form = document.getElementById("payment-form");
  const overlay = document.getElementById("loading-overlay");
  const payBtn = document.getElementById("submit-btn");

  form.addEventListener("submit", (e) => {
    e.preventDefault();

    overlay.style.display = "flex";
    payBtn.disabled = true;

    const clientSecret = document.getElementById("id_client_secret").value;
    const csrfToken = document.querySelector('input[name="csrfmiddlewaretoken"]').value;
    const saveInfo = document.querySelector('input[name="save_info"]')?.checked ? "true" : "false";
    const countryValue = document.getElementById("id_country")?.value?.trim();

    // Step 1: Cache checkout data in Django
    fetch(cacheCheckoutUrl, {
      method: "POST",
      headers: { "Content-Type": "application/x-www-form-urlencoded" },
      body: new URLSearchParams({
        csrfmiddlewaretoken: csrfToken,
        client_secret: clientSecret,
        save_info: saveInfo,
      }),
    })
      .then((res) => {
        if (!res.ok) throw new Error("Cache step failed");

        // Step 2: Confirm card payment

        return stripe.confirmCardPayment(clientSecret, {
          payment_method: {
            card: card,
            billing_details: {
              name: document.getElementById("id_full_name")?.value?.trim() || "",
              email: document.getElementById("id_email")?.value?.trim() || "",
              address: {
                line1: document.getElementById("id_street_address1")?.value?.trim() || "",
                line2: document.getElementById("id_street_address2")?.value?.trim() || "",
                city: document.getElementById("id_town_or_city")?.value?.trim() || "",
                postal_code: document.getElementById("id_postcode")?.value?.trim() || "",
                ...(countryValue ? { country: countryValue } : {}), // ✅ now excludes "" and " "
              },
            },
          },
          shipping: {
            name: document.getElementById("id_full_name")?.value?.trim() || "",
            address: {
              line1: document.getElementById("id_street_address1")?.value?.trim() || "",
              line2: document.getElementById("id_street_address2")?.value?.trim() || "",
              city: document.getElementById("id_town_or_city")?.value?.trim() || "",
              postal_code: document.getElementById("id_postcode")?.value?.trim() || "",
              ...(countryValue ? { country: countryValue } : {}), // ✅ same fix for shipping
            },
          },
        });
      })
      .then((result) => {
        if (result.error) {
          document.getElementById("card-errors").textContent = result.error.message;
          overlay.style.display = "none";
          payBtn.disabled = false;
        } else if (result.paymentIntent && result.paymentIntent.status === "succeeded") {
          document.getElementById("payment_intent_id").value = result.paymentIntent.id;
          form.submit();
        }
      })
      .catch((err) => {
        console.error(err);
        window.location.reload(); // fallback
      });
  });
});
