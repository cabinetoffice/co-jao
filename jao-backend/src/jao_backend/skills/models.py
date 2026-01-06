from django.db import models

class Skill(models.Model):
    """
    Stores a single, canonical skill, e.g., 'Python', 'Project Management'.
    """
    name = models.CharField(max_length=255, unique=True)
    cluster_id = models.IntegerField(default=-1, db_index=True)

    def __str__(self):
        return self.name
    

class SkillCluster(models.Model):
    """
    Stores the name of a skill cluster
    """
    cluster_id = models.IntegerField(primary_key=True)
    name = models.CharField(max_length=255, blank=True)

    def __str__(self):
        return self.name
