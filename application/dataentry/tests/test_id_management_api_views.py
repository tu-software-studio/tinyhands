from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIRequestFactory, APITestCase
from dataentry.models import Person, IntercepteeCommon
from dataentry.models import VictimInterview, BorderStation, Form
from accounts.tests.factories import SuperUserFactory
from dataentry.tests.factories import PersonFactory, CifIndiaFactory, IrfIndiaFactory, IntercepteeIndiaNoPhotoFactory, PersonBoxIndiaFactory, AliasGroupFactory
from dataentry.management.commands.formLatest import Command
from static_border_stations.tests.factories import GenericUserWithPermissions

class IDManagementTest(APITestCase):
    fixtures = ['initial-required-data/Region.json','initial-required-data/Country.json', 'initial-required-data/Permission.json']
    def setUp(self):
        self.phone_match = '9876543210'
        self.person_list = PersonFactory.create_batch(11)
        self.user = SuperUserFactory.create()
        GenericUserWithPermissions.add_permission(self.user, [{'group':'PERSON_MANAGEMENT', 'action':'EDIT', 'country': None, 'station': None},])
        self.client.force_authenticate(user=self.user)
        self.interceptee_list = IntercepteeIndiaNoPhotoFactory.create_batch(3)
        self.pb_list = PersonBoxIndiaFactory.create_batch(2)
        self.irf_list = IrfIndiaFactory.create_batch(2)
        self.cif_list = CifIndiaFactory.create_batch(2)

        self.interceptee_list[0].person = self.person_list[0]
        self.pb_list[0].person = self.person_list[0]
        self.pb_list[1].person = self.person_list[0]
        self.interceptee_list[1].person = self.person_list[1]
        self.cif_list[0].main_pv = self.person_list[2]
        self.interceptee_list[2].person = self.person_list[3]
        self.cif_list[1].main_pv = self.person_list[4]

        self.person_list[3].master_person = self.person_list[4].master_person

        self.person_list[3].phone_contact = self.phone_match + '01'
        self.person_list[4].phone_contact = self.phone_match + '02'

        self.person_list[3].full_name = "Raymond Smith"
        self.person_list[4].full_name = "Raymond Smythe"

        self.interceptee_list[0].interception_record = self.irf_list[0]
        self.interceptee_list[1].interception_record = self.irf_list[1]
        self.interceptee_list[2].interception_record = self.irf_list[1]

        self.pb_list[0].cif = self.cif_list[0]
        self.pb_list[1].cif = self.cif_list[1]

        for idx in range(0,3):
            self.interceptee_list[idx].save()

        for idx in range(0,2):
            self.pb_list[idx].save()

        for idx in range(0,2):
            self.cif_list[idx].save()

        for idx in range(0,5):
            self.person_list[idx].save()

    def test_list_persons(self):
        url = reverse('IDManagement')

        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['count'], 16)

    def test_fuzzy_search(self):
        url = reverse('IDManagementFuzzy')
        data = {'name': self.person_list[3].full_name}

        response = self.client.get(url, data)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 2)

    def test_phone_search(self):
        url = reverse('IDManagementPhone')
        data = {'phone': self.phone_match}

        response = self.client.get(url, data)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 2)

    def test_person_forms(self):
        command = Command()
        command.handle([],[])
        
        station = self.irf_list[0].station
        form = Form.objects.get(form_name='irfIndia')
        form.stations.add(station)
        form.save()
        
        url = reverse('IDManagementForms')
        data = {'person_id': self.person_list[0].id}

        response = self.client.get(url, data)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)

        cmpForm = []
        for idx in range(0, len(response.data)):
            cmpForm.append(response.data[idx]['number'])

        self.assertTrue(self.irf_list[0].irf_number in cmpForm, "missing irf")

    def test_add_alias(self):
        url = reverse('IDManagementAdd', args=[self.person_list[1].id, self.person_list[2].id])

        response = self.client.put(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        person1 = Person.objects.get(id=self.person_list[1].id)
        person2 = Person.objects.get(id=self.person_list[2].id)
        self.assertEqual(person1.master_person.id, person2.master_person.id)

    def test_alias_members(self):
        url = reverse('IDManagementGroup')
        data = {'group_id': self.person_list[3].master_person.id}

        response = self.client.get(url, data)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 2)

    def test_remove_alias(self):
        url = reverse('IDManagementRemove', args=[self.person_list[3].id])

        response = self.client.put(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        person1 = Person.objects.get(id=self.person_list[3].id)
        person2 = Person.objects.get(id=self.person_list[4].id)
        self.assertTrue(person1.master_person != person2.master_person, "master persons still match after remove")
