from django.db import models
from django.dispatch import receiver
from django.db.models.signals import post_save, pre_save, pre_delete
from django.db import transaction

PAID_CHOICES = (
    ('NO', 'Not Paid'),
    ('YES', 'Paid'),
)


class Tanker(models.Model):
    vehicle_no = models.CharField(max_length=10, unique=True)  # Ensure unique vehicle numbers
    vehicle_capacity = models.IntegerField()

    def __str__(self):
        return f"{self.vehicle_no} ({self.vehicle_capacity} liters)"


class Driver(models.Model):
    name = models.CharField(max_length=255)
    phone_no = models.CharField(max_length=20, unique=True)  # Ensure unique phone numbers for drivers

    def __str__(self):
        return f"{self.name} (Phone: {self.phone_no})"


class CustomerCategory(models.Model):
    name = models.CharField(max_length=255, unique=True)  # Enforce unique category names

    search_fields = ['name']

    def __str__(self):
        return self.name


class Customer(models.Model):
    name = models.CharField(max_length=255)
    address = models.CharField(max_length=500)
    category = models.ForeignKey(CustomerCategory, on_delete=models.PROTECT)  # Protect from category deletion
    pending_amount = models.FloatField()  # Use DecimalField for monetary values
    active = models.BooleanField(default=True)

    search_fields = ['name']

    def __str__(self):
        return f"{self.name} ({self.category})"


class Supply(models.Model):
    date = models.DateField()
    customer = models.ForeignKey(Customer, on_delete=models.PROTECT)  # Protect from customer deletion
    amount = models.FloatField()  # Use DecimalField for monetary values
    paid = models.CharField(max_length=10, choices=PAID_CHOICES, default='NO')  # Set default payment status
    tanker = models.ForeignKey(Tanker, on_delete=models.PROTECT)
    driver = models.ForeignKey(Driver, on_delete=models.SET_NULL, null=True)

    class Meta:
        ordering = ['date']

    def __repr__(self) -> str:
        return f"{str(self.date)}_{str(self.customer)}_{str(self.tanker)}"

    def __str__(self) -> str:
        return f"{str(self.date)}_{str(self.customer)}_{str(self.tanker)}"


@receiver(pre_save, sender=Supply)
def handle_supply_save(sender: models.Model, instance, **kwargs):
    try:
        old_instance = sender.objects.get(id=instance.id)
        if old_instance.paid.lower() != instance.paid.lower():
            if instance.paid.lower() == 'no':
                instance.customer.pending_amount += instance.amount
                pre_save.disconnect(handle_supply_save, sender=Supply)
                instance.customer.save()
                pre_save.connect(handle_supply_save, sender=Supply)
            elif instance.paid.lower() == 'yes':
                instance.customer.pending_amount -= instance.amount
                pre_save.disconnect(handle_supply_save, sender=Supply)
                instance.customer.save()
                pre_save.connect(handle_supply_save, sender=Supply)

    except sender.DoesNotExist:
        if instance.paid.lower() == 'no':
            instance.customer.pending_amount += instance.amount
            pre_save.disconnect(handle_supply_save, sender=Supply)
            instance.customer.save()
            pre_save.connect(handle_supply_save, sender=Supply)

@receiver(pre_delete, sender=Supply)
def handle_supply_delete(sender, instance, **kwargs):
    if instance.paid.lower() == 'no':
        raise Exception("Before deleting make sure pending amount is cleared")
    else:
        pass
