from dataclasses import dataclass
from typing import List, Optional
from procesos.models.TagKFUN import TagKFUN
from procesos.models.ArchivoKFUN import ArchivoKFUN

@dataclass
class FormatKFUN:
    l_tag: List[TagKFUN]
    l_archivo: List[ArchivoKFUN]
    general: Optional[str] = None