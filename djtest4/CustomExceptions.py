
class CustomAppError(Exception):
    def init(self, child_exceptions, err_msg):
        
        self.child_exceptions = child_exceptions
        self.err_msg = err_msg
        
    
    def __unicode__(self):
        
        return 'The following exceptions were raised: %s. Error message is: %s ' % self.child_exceptions, self.err_msg

        
    