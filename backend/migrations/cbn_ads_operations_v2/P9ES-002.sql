SET ANSI_NULLS ON;
SET QUOTED_IDENTIFIER ON;
SET ANSI_PADDING ON;
ALTER TABLE dbo.CRMPublicidadCaptacion DROP CONSTRAINT CK_P9Captacion;
ALTER TABLE dbo.CRMPublicidadCaptacion WITH CHECK ADD CONSTRAINT CK_P9CaptacionV2 CHECK(Kind IN('lead','comment') AND Channel IN('facebook','instagram','tiktok') AND Origin IN('operator','verified_receipt','synthetic_demo') AND State IN('new','review','qualified','converted','lost','resolved','ignored','hidden','deleted') AND Revision>0 AND ISJSON(Document)=1);
ALTER TABLE dbo.CRMPublicidadCaptacion WITH CHECK ADD CONSTRAINT CK_P9CaptacionVinculo CHECK((IdentityId IS NULL AND ConvertedAt IS NULL AND State<>'converted') OR (IdentityId IS NOT NULL AND ConvertedAt IS NOT NULL));
