"""
Tests for the provided models.
"""
import pix


def test_project_metaclass_loader():
    """
    Tests projects load and become the active project when methods are called
    """
    class MyProject(pix.PIXProject):
        def foo(self):
            pass

    session = pix.Session()
    assert session.active_project is None

    # make a bogus project instance
    project = MyProject(session.factory, id='myid')
    # call our custom method
    project.foo()
    # confirm auto-activate worked
    assert session.active_project is project
