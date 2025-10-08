import os
from app.wordpress import WordPressClient
from app.config import WORDPRESS_CONFIG, WORDPRESS_CATEGORIES

def test_create_post_with_new_category():
    """
    Tests creating a post with a new category.
    """
    # It's dangerous to run this test against a production WordPress instance.
    # This is a placeholder for a real test with a mock WordPress API.
    # In a real-world scenario, we would use a library like `requests-mock`
    # to simulate the WordPress API responses.
    
    # For now, we will just print the configuration and the payload
    # to demonstrate that the logic is correct.

    print("--- Testing Category Creation ---")

    # Create a WordPress client
    client = WordPressClient(WORDPRESS_CONFIG, WORDPRESS_CATEGORIES)

    # Define a payload with a new category
    new_category_name = "new-test-category"
    payload = {
        "title": "Test Post with New Category",
        "content": "This is a test post.",
        "categories": [new_category_name],
        "status": "draft" # Use draft status to avoid polluting the production site
    }

    print(f"Attempting to create a post with a new category: '{new_category_name}'")
    
    # In a real test, we would mock this call and assert the response.
    # For now, we will just print the payload that would be sent.
    
    # Resolve category names to IDs
    if 'categories' in payload and payload['categories']:
        cat_input = payload['categories']
        if isinstance(cat_input, (int, str)):
            cat_input = [cat_input]
        
        category_names = [str(c) for c in cat_input if isinstance(c, str) and not c.isdigit()]
        category_ids = [int(c) for c in cat_input if isinstance(c, int) or (isinstance(c, str) and c.isdigit())]
        
        if category_names:
            # This is the function that should create the category
            resolved_ids = client.resolve_category_names_to_ids(category_names)
            category_ids.extend(resolved_ids)
        
        payload['categories'] = list(set(category_ids))

    print("Payload to be sent to WordPress:")
    print(payload)

    # Here you would typically make the call to `client.create_post(payload)`
    # and assert that the post was created with the correct category ID.

    print("--- Test Finished ---")
    print("NOTE: This is a dry run. No actual post was created.")
    print("To complete this test, you would need to mock the WordPress API calls.")


if __name__ == "__main__":
    test_create_post_with_new_category()