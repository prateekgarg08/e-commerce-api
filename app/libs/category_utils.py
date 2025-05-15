from bson import ObjectId

async def get_descendant_category_ids(category_id, db):
    """
    Recursively fetch all descendant category IDs (including the given one).
    Args:
        category_id (str or ObjectId): The root category ID.
        db: The database instance (should have a 'categories' collection).
    Returns:
        List[ObjectId]: List of all descendant category ObjectIds (including the root).
    """
    if not isinstance(category_id, ObjectId):
        category_id = ObjectId(category_id)
    all_ids = [category_id]
    queue = [category_id]
    while queue:
        current_id = queue.pop(0)
        children = await db.categories.find({"parent_id": current_id}).to_list(1000)
        for child in children:
            child_id = child["_id"]
            all_ids.append(child_id)
            queue.append(child_id)
    return all_ids 